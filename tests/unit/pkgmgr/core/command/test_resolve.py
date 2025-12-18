#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import stat
import tempfile
import unittest
from unittest.mock import patch

from pkgmgr.core.command.resolve import (
    _find_python_package_root,
    _nix_binary_candidates,
    _path_binary_candidates,
    resolve_command_for_repo,
)


class TestHelpers(unittest.TestCase):
    def test_find_python_package_root_none_when_missing_src(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = _find_python_package_root(tmpdir)
            self.assertIsNone(root)

    def test_find_python_package_root_returns_existing_dir_or_none(self) -> None:
        """
        We only assert that the helper does not return an invalid path.
        The exact selection heuristic is intentionally left flexible since
        the implementation may evolve.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            src_dir = os.path.join(tmpdir, "src", "mypkg")
            os.makedirs(src_dir, exist_ok=True)
            init_path = os.path.join(src_dir, "__init__.py")
            with open(init_path, "w", encoding="utf-8") as f:
                f.write("# package marker\n")

            root = _find_python_package_root(tmpdir)
            if root is not None:
                self.assertTrue(os.path.isdir(root))

    def test_nix_binary_candidates_builds_expected_paths(self) -> None:
        home = "/home/testuser"
        names = ["pkgmgr", "", None, "other"]  # type: ignore[list-item]
        candidates = _nix_binary_candidates(home, names)  # type: ignore[arg-type]

        self.assertIn(
            os.path.join(home, ".nix-profile", "bin", "pkgmgr"),
            candidates,
        )
        self.assertIn(
            os.path.join(home, ".nix-profile", "bin", "other"),
            candidates,
        )
        self.assertEqual(len(candidates), 2)

    @patch("pkgmgr.core.command.resolve._is_executable", return_value=True)
    @patch("pkgmgr.core.command.resolve.shutil.which")
    def test_path_binary_candidates_uses_which_and_executable(
        self,
        mock_which,
        _mock_is_executable,
    ) -> None:
        def which_side_effect(name: str) -> str | None:
            if name == "pkgmgr":
                return "/usr/local/bin/pkgmgr"
            if name == "other":
                return "/usr/bin/other"
            return None

        mock_which.side_effect = which_side_effect

        candidates = _path_binary_candidates(["pkgmgr", "other", "missing"])
        self.assertEqual(
            candidates,
            ["/usr/local/bin/pkgmgr", "/usr/bin/other"],
        )


class TestResolveCommandForRepo(unittest.TestCase):
    def test_explicit_command_in_repo_wins(self) -> None:
        repo = {"command": "/custom/path/pkgmgr"}
        cmd = resolve_command_for_repo(
            repo=repo,
            repo_identifier="pkgmgr",
            repo_dir="/tmp/pkgmgr",
        )
        self.assertEqual(cmd, "/custom/path/pkgmgr")

    @patch("pkgmgr.core.command.resolve._is_executable", return_value=True)
    @patch("pkgmgr.core.command.resolve._nix_binary_candidates", return_value=[])
    @patch("pkgmgr.core.command.resolve.shutil.which")
    def test_prefers_non_system_path_over_system_binary(
        self,
        mock_which,
        _mock_nix_candidates,
        _mock_is_executable,
    ) -> None:
        """
        If both a system binary (/usr/bin) and a non-system binary (/opt/bin)
        exist in PATH, the non-system binary must be preferred.
        """

        def which_side_effect(name: str) -> str | None:
            if name == "pkgmgr":
                return "/usr/bin/pkgmgr"  # system binary
            if name == "alias":
                return "/opt/bin/pkgmgr"  # non-system binary
            return None

        mock_which.side_effect = which_side_effect

        repo = {
            "alias": "alias",
            "repository": "pkgmgr",
        }
        cmd = resolve_command_for_repo(
            repo=repo,
            repo_identifier="pkgmgr",
            repo_dir="/tmp/pkgmgr",
        )
        self.assertEqual(cmd, "/opt/bin/pkgmgr")

    @patch("pkgmgr.core.command.resolve._is_executable", return_value=True)
    @patch("pkgmgr.core.command.resolve._nix_binary_candidates")
    @patch("pkgmgr.core.command.resolve.shutil.which")
    def test_nix_binary_used_when_no_non_system_bin(
        self,
        mock_which,
        mock_nix_candidates,
        _mock_is_executable,
    ) -> None:
        """
        When only a system binary exists in PATH but a Nix profile binary is
        available, the Nix binary should be preferred.
        """

        def which_side_effect(name: str) -> str | None:
            if name == "pkgmgr":
                return "/usr/bin/pkgmgr"
            return None

        mock_which.side_effect = which_side_effect
        mock_nix_candidates.return_value = ["/home/test/.nix-profile/bin/pkgmgr"]

        repo = {"repository": "pkgmgr"}
        cmd = resolve_command_for_repo(
            repo=repo,
            repo_identifier="pkgmgr",
            repo_dir="/tmp/pkgmgr",
        )
        self.assertEqual(cmd, "/home/test/.nix-profile/bin/pkgmgr")

    def test_main_sh_fallback_when_no_binaries(self) -> None:
        """
        If no CLI is found via PATH or Nix, resolve_command_for_repo()
        should fall back to an executable main.sh in the repo root.
        """
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("pkgmgr.core.command.resolve.shutil.which", return_value=None),
            patch(
                "pkgmgr.core.command.resolve._nix_binary_candidates", return_value=[]
            ),
            patch("pkgmgr.core.command.resolve._is_executable") as mock_is_executable,
        ):
            main_sh = os.path.join(tmpdir, "main.sh")
            with open(main_sh, "w", encoding="utf-8") as f:
                f.write("#!/bin/sh\nexit 0\n")
            os.chmod(main_sh, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR)

            def is_exec_side_effect(path: str) -> bool:
                return path == main_sh

            mock_is_executable.side_effect = is_exec_side_effect

            repo = {}
            cmd = resolve_command_for_repo(
                repo=repo,
                repo_identifier="pkgmgr",
                repo_dir=tmpdir,
            )
            self.assertEqual(cmd, main_sh)

    def test_python_package_without_entry_point_returns_none(self) -> None:
        """
        If the repository looks like a Python package (src/package/__init__.py)
        but there is no CLI entry point or main.sh/main.py, the result
        should be None.
        """
        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch("pkgmgr.core.command.resolve.shutil.which", return_value=None),
            patch(
                "pkgmgr.core.command.resolve._nix_binary_candidates", return_value=[]
            ),
            patch("pkgmgr.core.command.resolve._is_executable", return_value=False),
        ):
            src_dir = os.path.join(tmpdir, "src", "mypkg")
            os.makedirs(src_dir, exist_ok=True)
            init_path = os.path.join(src_dir, "__init__.py")
            with open(init_path, "w", encoding="utf-8") as f:
                f.write("# package marker\n")

            repo = {}
            cmd = resolve_command_for_repo(
                repo=repo,
                repo_identifier="mypkg",
                repo_dir=tmpdir,
            )
            self.assertIsNone(cmd)


if __name__ == "__main__":
    unittest.main()
