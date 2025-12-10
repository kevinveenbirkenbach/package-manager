import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

from pkgmgr.core.command.resolve import resolve_command_for_repo


class TestResolveCommandForRepo(unittest.TestCase):

    # ----------------------------------------------------------------------
    # Helper: Create a fake src/<pkg>/__main__.py for Python package detection
    # ----------------------------------------------------------------------
    def _create_python_package(self, repo_dir, package_name="mypkg"):
        src = os.path.join(repo_dir, "src", package_name)
        os.makedirs(src, exist_ok=True)
        main_file = os.path.join(src, "__main__.py")
        with open(main_file, "w", encoding="utf-8") as f:
            f.write("# fake python package entry\n")
        return main_file

    # ----------------------------------------------------------------------
    # 1) Python package but no installed command → must fail with SystemExit
    # ----------------------------------------------------------------------
    def test_python_package_without_installed_command_raises(self):
        with tempfile.TemporaryDirectory() as repo_dir:

            # Fake Python package src/.../__main__.py
            self._create_python_package(repo_dir)

            repo = {}
            repo_identifier = "analysis-ready-code"

            with patch("shutil.which", return_value=None):
                with self.assertRaises(SystemExit) as ctx:
                    resolve_command_for_repo(repo, repo_identifier, repo_dir)

            self.assertIn("Python package", str(ctx.exception))

    # ----------------------------------------------------------------------
    # 2) Python package with installed command via PATH → returns command
    # ----------------------------------------------------------------------
    def test_python_package_with_installed_command(self):
        with tempfile.TemporaryDirectory() as repo_dir:

            # Fake python package
            self._create_python_package(repo_dir)

            repo = {}
            repo_identifier = "analysis-ready-code"

            fake_binary = os.path.join(repo_dir, "fakebin", "analysis-ready-code")
            os.makedirs(os.path.dirname(fake_binary), exist_ok=True)
            with open(fake_binary, "w") as f:
                f.write("#!/bin/sh\necho test\n")
            os.chmod(fake_binary, 0o755)

            with patch("shutil.which", return_value=fake_binary):
                result = resolve_command_for_repo(repo, repo_identifier, repo_dir)
                self.assertEqual(result, fake_binary)

    # ----------------------------------------------------------------------
    # 3) Script repo: return main.py if present
    # ----------------------------------------------------------------------
    def test_script_repo_fallback_main_py(self):
        with tempfile.TemporaryDirectory() as repo_dir:

            fake_main = os.path.join(repo_dir, "main.py")
            with open(fake_main, "w", encoding="utf-8") as f:
                f.write("# script\n")

            repo = {}
            repo_identifier = "myscript"

            with patch("shutil.which", return_value=None):
                result = resolve_command_for_repo(repo, repo_identifier, repo_dir)
                self.assertEqual(result, fake_main)

    # ----------------------------------------------------------------------
    # 4) Explicit command has highest priority
    # ----------------------------------------------------------------------
    def test_explicit_command(self):
        with tempfile.TemporaryDirectory() as repo_dir:
            repo = {"command": "/custom/runner.sh"}
            repo_identifier = "x"

            result = resolve_command_for_repo(repo, repo_identifier, repo_dir)
            self.assertEqual(result, "/custom/runner.sh")


if __name__ == "__main__":
    unittest.main()
