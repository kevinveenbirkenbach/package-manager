#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for recursive capability resolution and installer shadowing.

These tests verify that, given different repository layouts (Makefile, pyproject,
flake.nix, PKGBUILD), only the expected installers are executed based on the
capabilities provided by higher layers.

Layer order (strongest → weakest):

  OS-PACKAGES  >  NIX  >  PYTHON  >  MAKEFILE
"""

import os
import shutil
import tempfile
import unittest
from typing import List, Sequence, Tuple
from unittest.mock import patch

import pkgmgr.actions.install as install_mod
from pkgmgr.actions.install import install_repos
from pkgmgr.actions.install.installers.makefile import MakefileInstaller
from pkgmgr.actions.install.installers.nix import NixFlakeInstaller
from pkgmgr.actions.install.installers.os_packages.arch_pkgbuild import (
    ArchPkgbuildInstaller,
)
from pkgmgr.actions.install.installers.python import PythonInstaller


InstallerSpec = Tuple[str, object]


class TestRecursiveCapabilitiesIntegration(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_root = tempfile.mkdtemp(prefix="pkgmgr-recursive-caps-")
        self.bin_dir = os.path.join(self.tmp_root, "bin")
        os.makedirs(self.bin_dir, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_root)

    # ------------------------------------------------------------------ helpers

    def _new_repo(self) -> str:
        """
        Create a fresh temporary repo directory under self.tmp_root.
        """
        return tempfile.mkdtemp(prefix="repo-", dir=self.tmp_root)

    def _run_with_installers(
        self,
        repo_dir: str,
        installers: Sequence[InstallerSpec],
        selected_repos=None,
    ) -> List[str]:
        """
        Run install_repos() with a custom INSTALLERS list and capture which
        installer labels actually run.

        We override each installer's supports() to always return True and
        override run() to append its label to called_installers.
        """
        if selected_repos is None:
            repo = {"repository": "dummy"}
            selected_repos = [repo]
            all_repos = [repo]
        else:
            all_repos = selected_repos

        called_installers: List[str] = []

        patched_installers = []
        for label, inst in installers:
            def always_supports(self, ctx):
                return True

            def make_run(label_name: str):
                def _run(self, ctx):
                    called_installers.append(label_name)
                return _run

            inst.supports = always_supports.__get__(inst, inst.__class__)  # type: ignore[assignment]
            inst.run = make_run(label).__get__(inst, inst.__class__)  # type: ignore[assignment]
            patched_installers.append(inst)

        with patch.object(install_mod, "INSTALLERS", patched_installers), patch.object(
            install_mod, "get_repo_identifier", return_value="dummy-repo"
        ), patch.object(
            install_mod, "get_repo_dir", return_value=repo_dir
        ), patch.object(
            install_mod, "verify_repository", return_value=(True, [], None, None)
        ), patch.object(
            install_mod, "clone_repos"
        ):
            install_repos(
                selected_repos=selected_repos,
                repositories_base_dir=self.tmp_root,
                bin_dir=self.bin_dir,
                all_repos=all_repos,
                no_verification=True,
                preview=False,
                quiet=False,
                clone_mode="ssh",
                update_dependencies=False,
            )

        return called_installers

    # ----------------------------------------------------------------- scenarios

    def test_only_makefile_installer_runs(self) -> None:
        """
        With only a Makefile present, only the MakefileInstaller should run.
        """
        repo_dir = self._new_repo()

        with open(os.path.join(repo_dir, "Makefile"), "w", encoding="utf-8") as f:
            f.write("install:\n\t@echo 'make install'\n")

        mk_inst = MakefileInstaller()
        installers: Sequence[InstallerSpec] = [("makefile", mk_inst)]

        called = self._run_with_installers(repo_dir, installers)

        self.assertEqual(
            called,
            ["makefile"],
            "With only a Makefile, the MakefileInstaller should run exactly once.",
        )

    def test_python_and_makefile_both_run_when_caps_disjoint(self) -> None:
        """
        If Python and Makefile have disjoint capabilities, both installers run.
        """
        repo_dir = self._new_repo()

        # pyproject.toml without any explicit "make install" hint
        with open(os.path.join(repo_dir, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write("name = 'dummy'\n")

        with open(os.path.join(repo_dir, "Makefile"), "w", encoding="utf-8") as f:
            f.write("install:\n\t@echo 'make install'\n")

        py_inst = PythonInstaller()
        mk_inst = MakefileInstaller()
        installers: Sequence[InstallerSpec] = [
            ("python", py_inst),
            ("makefile", mk_inst),
        ]

        called = self._run_with_installers(repo_dir, installers)

        self.assertEqual(
            called,
            ["python", "makefile"],
            "PythonInstaller and MakefileInstaller should both run when their "
            "capabilities are disjoint.",
        )

    def test_python_shadows_makefile_when_pyproject_mentions_make_install(self) -> None:
        """
        If the Python layer advertises a 'make-install' capability (pyproject
        explicitly hints at 'make install'), the Makefile layer must be skipped.
        """
        repo_dir = self._new_repo()

        with open(os.path.join(repo_dir, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write(
                "name = 'dummy'\n"
                "\n"
                "# Hint for MakeInstallCapability on layer 'python'\n"
                "make install\n"
            )

        with open(os.path.join(repo_dir, "Makefile"), "w", encoding="utf-8") as f:
            f.write("install:\n\t@echo 'make install'\n")

        py_inst = PythonInstaller()
        mk_inst = MakefileInstaller()
        installers: Sequence[InstallerSpec] = [
            ("python", py_inst),
            ("makefile", mk_inst),
        ]

        called = self._run_with_installers(repo_dir, installers)

        self.assertIn("python", called, "PythonInstaller should have run.")
        self.assertNotIn(
            "makefile",
            called,
            "MakefileInstaller should be skipped because its 'make-install' "
            "capability is already provided by Python.",
        )

    def test_nix_shadows_python_and_makefile(self) -> None:
        """
        If a Nix flake advertises both python-runtime and make-install
        capabilities, Python and Makefile installers must be skipped.
        """
        repo_dir = self._new_repo()

        with open(os.path.join(repo_dir, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write("name = 'dummy'\n")

        with open(os.path.join(repo_dir, "Makefile"), "w", encoding="utf-8") as f:
            f.write("install:\n\t@echo 'make install'\n")

        with open(os.path.join(repo_dir, "flake.nix"), "w", encoding="utf-8") as f:
            f.write(
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
        installers: Sequence[InstallerSpec] = [
            ("nix", nix_inst),
            ("python", py_inst),
            ("makefile", mk_inst),
        ]

        called = self._run_with_installers(repo_dir, installers)

        self.assertIn("nix", called, "NixFlakeInstaller should have run.")
        self.assertNotIn(
            "python",
            called,
            "PythonInstaller should be skipped because its python-runtime "
            "capability is already provided by Nix.",
        )
        self.assertNotIn(
            "makefile",
            called,
            "MakefileInstaller should be skipped because its make-install "
            "capability is already provided by Nix.",
        )

    def test_os_packages_shadow_nix_python_and_makefile(self) -> None:
        """
        If an OS package layer (PKGBUILD) advertises all capabilities,
        all lower layers (Nix, Python, Makefile) must be skipped.
        """
        repo_dir = self._new_repo()

        with open(os.path.join(repo_dir, "pyproject.toml"), "w", encoding="utf-8") as f:
            f.write("name = 'dummy'\n")

        with open(os.path.join(repo_dir, "Makefile"), "w", encoding="utf-8") as f:
            f.write("install:\n\t@echo 'make install'\n")

        with open(os.path.join(repo_dir, "flake.nix"), "w", encoding="utf-8") as f:
            f.write(
                '  description = "integration test flake";\n'
                "}\n"
                "\n"
                "buildPythonApplication something\n"
                "make install\n"
            )

        with open(os.path.join(repo_dir, "PKGBUILD"), "w", encoding="utf-8") as f:
            f.write(
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
        installers: Sequence[InstallerSpec] = [
            ("os-packages", os_inst),
            ("nix", nix_inst),
            ("python", py_inst),
            ("makefile", mk_inst),
        ]

        called = self._run_with_installers(repo_dir, installers)

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
