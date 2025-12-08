#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for the recursive / layered capability handling in pkgmgr.

We focus on the interaction between:

  - MakefileInstaller     (layer: "makefile")
  - PythonInstaller       (layer: "python")
  - NixFlakeInstaller     (layer: "nix")
  - ArchPkgbuildInstaller (layer: "os-packages")

The core idea:

  - Each installer declares logical capabilities for its layer via
    discover_capabilities() and the global CAPABILITY_MATCHERS.
  - install_repos() tracks which capabilities have already been provided
    by earlier installers (in INSTALLERS order).
  - If an installer only provides capabilities that are already covered
    by previous installers, it is skipped.

These tests use *real* capability detection (based on repo files like
flake.nix, pyproject.toml, Makefile, PKGBUILD), but patch the installers'
run() methods so that no real external commands are executed.

Scenarios:

  1. Only Makefile with install target
       → MakefileInstaller runs, all good.

  2. Python + Makefile (no "make install" in pyproject.toml)
       → PythonInstaller provides only python-runtime
       → MakefileInstaller provides make-install
       → Both run, since their capabilities are disjoint.

  3. Python + Makefile (pyproject.toml mentions "make install")
       → PythonInstaller provides {python-runtime, make-install}
       → MakefileInstaller provides {make-install}
       → MakefileInstaller is skipped (capabilities already covered).

  4. Nix + Python + Makefile
       - flake.nix hints:
           * buildPythonApplication (python-runtime)
           * make install        (make-install)
       → NixFlakeInstaller provides {python-runtime, make-install, nix-flake}
       → PythonInstaller and MakefileInstaller are skipped.

  5. OS packages + Nix + Python + Makefile
       - PKGBUILD contains:
           * "pip install ."   (python-runtime via os-packages)
           * "make install"    (make-install via os-packages)
           * "nix profile"     (nix-flake via os-packages)
       → ArchPkgbuildInstaller provides all capabilities
       → All lower layers are skipped.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

import pkgmgr.install_repos as install_mod
from pkgmgr.install_repos import install_repos
from pkgmgr.installers.nix_flake import NixFlakeInstaller
from pkgmgr.installers.python import PythonInstaller
from pkgmgr.installers.makefile import MakefileInstaller
from pkgmgr.installers.os_packages.arch_pkgbuild import ArchPkgbuildInstaller


class TestRecursiveCapabilitiesIntegration(unittest.TestCase):
    def setUp(self) -> None:
        # Temporary base directory for this test class
        self.tmp_root = tempfile.mkdtemp(prefix="pkgmgr-integration-")
        self.bin_dir = os.path.join(self.tmp_root, "bin")
        os.makedirs(self.bin_dir, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_root)

    # ------------------------------------------------------------------
    # Helper: create a new repo directory for a scenario
    # ------------------------------------------------------------------
    def _new_repo(self) -> str:
        repo_dir = tempfile.mkdtemp(prefix="repo-", dir=self.tmp_root)
        return repo_dir

    # ------------------------------------------------------------------
    # Helper: run install_repos() with a custom installer list
    #         and record which installers actually ran.
    # ------------------------------------------------------------------
    def _run_with_installers(self, repo_dir: str, installers, selected_repos=None):
        """
        Run install_repos() with a given INSTALLERS list and a single
        dummy repo; return the list of installer labels that actually ran.

        The installers' supports() are forced to True so that only the
        capability-shadowing logic decides whether they are skipped.
        The installers' run() methods are patched to avoid real commands.
        """
        if selected_repos is None:
            repo = {}
            selected_repos = [repo]
            all_repos = [repo]
        else:
            all_repos = selected_repos

        called_installers: list[str] = []

        # Prepare patched instances with recording run() and always-supports.
        patched_installers = []
        for label, inst in installers:
            def always_supports(self, ctx):
                return True

            def make_run(label_name):
                def _run(self, ctx):
                    called_installers.append(label_name)
                return _run

            inst.supports = always_supports.__get__(inst, inst.__class__)
            inst.run = make_run(label).__get__(inst, inst.__class__)
            patched_installers.append(inst)

        with patch.object(install_mod, "INSTALLERS", patched_installers), \
             patch.object(install_mod, "get_repo_identifier", return_value="dummy-repo"), \
             patch.object(install_mod, "get_repo_dir", return_value=repo_dir), \
             patch.object(install_mod, "verify_repository", return_value=(True, [], None, None)), \
             patch.object(install_mod, "create_ink"), \
             patch.object(install_mod, "clone_repos"):

            install_repos(
                selected_repos=selected_repos,
                repositories_base_dir=self.tmp_root,
                bin_dir=self.bin_dir,
                all_repos=all_repos,
                no_verification=True,
                preview=False,
                quiet=False,
                clone_mode="shallow",
                update_dependencies=False,
            )

        return called_installers

    # ------------------------------------------------------------------
    # Scenario 1: Only Makefile with install target
    # ------------------------------------------------------------------
    def test_only_makefile_installer_runs(self) -> None:
        repo_dir = self._new_repo()

        # Makefile: detect a real 'install' target for makefile layer.
        with open(os.path.join(repo_dir, "Makefile"), "w", encoding="utf-8") as f:
            f.write("install:\n\t@echo 'installing from Makefile'\n")

        mk_inst = MakefileInstaller()
        installers = [("makefile", mk_inst)]

        called = self._run_with_installers(repo_dir, installers)

        self.assertEqual(
            called,
            ["makefile"],
            "With only a Makefile, the MakefileInstaller should run exactly once.",
        )

    # ------------------------------------------------------------------
    # Scenario 2: Python + Makefile, but pyproject.toml does NOT mention 'make install'
    #             → capabilities are disjoint, both installers should run.
    # ------------------------------------------------------------------
    def test_python_and_makefile_both_run_when_caps_disjoint(self) -> None:
        repo_dir = self._new_repo()

        # pyproject.toml: basic Python project, no 'make install' string.
        with open(os.path.join(repo_dir, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write(
                "[project]\n"
                "name = 'dummy'\n"
            )

        # Makefile: install target for makefile layer.
        with open(os.path.join(repo_dir, "Makefile"), "w", encoding="utf-8") as f:
            f.write("install:\n\t@echo 'installing from Makefile'\n")

        py_inst = PythonInstaller()
        mk_inst = MakefileInstaller()

        # Order: Python first, then Makefile
        installers = [
            ("python", py_inst),
            ("makefile", mk_inst),
        ]

        called = self._run_with_installers(repo_dir, installers)

        # Both should have run because:
        #   - Python provides {python-runtime}
        #   - Makefile provides {make-install}
        self.assertEqual(
            called,
            ["python", "makefile"],
            "PythonInstaller and MakefileInstaller should both run when their capabilities are disjoint.",
        )

    # ------------------------------------------------------------------
    # Scenario 3: Python + Makefile, pyproject.toml mentions 'make install'
    #             → PythonInstaller provides {python-runtime, make-install}
    #               MakefileInstaller only {make-install}
    #             → MakefileInstaller must be skipped.
    # ------------------------------------------------------------------
    def test_python_shadows_makefile_when_pyproject_mentions_make_install(self) -> None:
        repo_dir = self._new_repo()

        # pyproject.toml: Python project with 'make install' hint.
        with open(os.path.join(repo_dir, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write(
                "[project]\n"
                "name = 'dummy'\n"
                "\n"
                "# Hint for MakeInstallCapability on layer 'python'\n"
                "make install\n"
            )

        # Makefile: install target, but should be shadowed by Python.
        with open(os.path.join(repo_dir, "Makefile"), "w", encoding="utf-8") as f:
            f.write("install:\n\t@echo 'installing from Makefile'\n")

        py_inst = PythonInstaller()
        mk_inst = MakefileInstaller()

        installers = [
            ("python", py_inst),
            ("makefile", mk_inst),
        ]

        called = self._run_with_installers(repo_dir, installers)

        # Python should run, Makefile should be skipped because its only
        # capability (make-install) is already provided by Python.
        self.assertIn("python", called, "PythonInstaller should have run.")
        self.assertNotIn(
            "makefile",
            called,
            "MakefileInstaller should be skipped because its 'make-install' capability "
            "is already provided by Python.",
        )

    # ------------------------------------------------------------------
    # Scenario 4: Nix + Python + Makefile
    #             flake.nix provides python-runtime + make-install + nix-flake
    #             → Nix shadows both Python and Makefile.
    # ------------------------------------------------------------------
    def test_nix_shadows_python_and_makefile(self) -> None:
        repo_dir = self._new_repo()

        # pyproject.toml: generic Python project
        with open(os.path.join(repo_dir, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write(
                "[project]\n"
                "name = 'dummy'\n"
            )

        # Makefile: install target
        with open(os.path.join(repo_dir, "Makefile"), "w", encoding="utf-8") as f:
            f.write("install:\n\t@echo 'installing from Makefile'\n")

        # flake.nix: hints for both python-runtime and make-install on layer 'nix'
        with open(os.path.join(repo_dir, "flake.nix"), "w", encoding="utf-8") as f:
            f.write(
                "{\n"
                '  description = "integration test flake";\n'
                "}\n"
                "\n"
                "# Hint for PythonRuntimeCapability on layer 'nix'\n"
                "buildPythonApplication something\n"
                "\n"
                "# Hint for MakeInstallCapability on layer 'nix'\n"
                "make install\n"
            )

        nix_inst = NixFlakeInstaller()
        py_inst = PythonInstaller()
        mk_inst = MakefileInstaller()

        installers = [
            ("nix", nix_inst),
            ("python", py_inst),
            ("makefile", mk_inst),
        ]

        called = self._run_with_installers(repo_dir, installers)

        # Nix must run, Python and Makefile must be skipped:
        #   - Nix provides {python-runtime, make-install, nix-flake}
        #   - Python provides {python-runtime}
        #   - Makefile provides {make-install}
        self.assertIn("nix", called, "NixFlakeInstaller should have run.")
        self.assertNotIn(
            "python",
            called,
            "PythonInstaller should be skipped because its python-runtime capability "
            "is already provided by Nix.",
        )
        self.assertNotIn(
            "makefile",
            called,
            "MakefileInstaller should be skipped because its make-install capability "
            "is already provided by Nix.",
        )

    # ------------------------------------------------------------------
    # Scenario 5: OS packages + Nix + Python + Makefile
    #             PKGBUILD provides python-runtime + make-install + nix-flake
    #             → ArchPkgbuildInstaller shadows everything below.
    # ------------------------------------------------------------------
    def test_os_packages_shadow_nix_python_and_makefile(self) -> None:
        repo_dir = self._new_repo()

        # pyproject.toml: enough to signal a Python project
        with open(os.path.join(repo_dir, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write(
                "[project]\n"
                "name = 'dummy'\n"
            )

        # Makefile: install target
        with open(os.path.join(repo_dir, "Makefile"), "w", encoding="utf-8") as f:
            f.write("install:\n\t@echo 'installing from Makefile'\n")

        # flake.nix: as before
        with open(os.path.join(repo_dir, "flake.nix"), "w", encoding="utf-8") as f:
            f.write(
                "{\n"
                '  description = "integration test flake";\n'
                "}\n"
                "\n"
                "buildPythonApplication something\n"
                "make install\n"
            )

        # PKGBUILD: contains patterns for all three capabilities on layer 'os-packages':
        #   - "pip install ."   → python-runtime
        #   - "make install"    → make-install
        #   - "nix profile"     → nix-flake
        with open(os.path.join(repo_dir, "PKGBUILD"), "w", encoding="utf-8") as f:
            f.write(
                "pkgname=dummy\n"
                "pkgver=0.1\n"
                "pkgrel=1\n"
                "pkgdesc='dummy pkg for integration test'\n"
                "arch=('any')\n"
                "source=()\n"
                "sha256sums=()\n"
                "\n"
                "build() {\n"
                "  echo 'build phase'\n"
                "}\n"
                "\n"
                "package() {\n"
                "  echo 'install via pip and make and nix'\n"
                "  pip install .\n"
                "  make install\n"
                "  nix profile list || true\n"
                "}\n"
            )

        os_inst = ArchPkgbuildInstaller()
        nix_inst = NixFlakeInstaller()
        py_inst = PythonInstaller()
        mk_inst = MakefileInstaller()

        installers = [
            ("os-packages", os_inst),
            ("nix", nix_inst),
            ("python", py_inst),
            ("makefile", mk_inst),
        ]

        called = self._run_with_installers(repo_dir, installers)

        # ArchPkgbuildInstaller must run, and everything below must be skipped:
        #   - os-packages provides {python-runtime, make-install, nix-flake}
        #   - nix provides {python-runtime, make-install, nix-flake}
        #   - python provides {python-runtime}
        #   - makefile provides {make-install}
        self.assertIn("os-packages", called, "ArchPkgbuildInstaller should have run.")
        self.assertNotIn(
            "nix",
            called,
            "NixFlakeInstaller should be skipped because all its capabilities "
            "are already provided by os-packages.",
        )
        self.assertNotIn(
            "python",
            called,
            "PythonInstaller should be skipped because python-runtime is already "
            "provided by os-packages.",
        )
        self.assertNotIn(
            "makefile",
            called,
            "MakefileInstaller should be skipped because make-install is already "
            "provided by os-packages.",
        )


if __name__ == "__main__":
    unittest.main()
