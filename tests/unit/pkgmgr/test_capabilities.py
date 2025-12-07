# tests/unit/pkgmgr/test_capabilities.py

import os
import unittest
from unittest.mock import patch, mock_open

from pkgmgr.capabilities import (
    PythonRuntimeCapability,
    MakeInstallCapability,
    NixFlakeCapability,
)


class DummyCtx:
    """Minimal RepoContext stub with just repo_dir."""
    def __init__(self, repo_dir: str):
        self.repo_dir = repo_dir


class TestCapabilities(unittest.TestCase):
    def setUp(self):
        self.ctx = DummyCtx("/tmp/repo")

    @patch("pkgmgr.capabilities.os.path.exists")
    def test_python_runtime_python_layer_pyproject(self, mock_exists):
        cap = PythonRuntimeCapability()

        def exists_side_effect(path):
            return path.endswith("pyproject.toml")

        mock_exists.side_effect = exists_side_effect

        self.assertTrue(cap.applies_to_layer("python"))
        self.assertTrue(cap.is_provided(self.ctx, "python"))

    @patch("pkgmgr.capabilities._read_text_if_exists")
    @patch("pkgmgr.capabilities.os.path.exists")
    def test_python_runtime_nix_layer_flake(self, mock_exists, mock_read):
        cap = PythonRuntimeCapability()

        def exists_side_effect(path):
            return path.endswith("flake.nix")

        mock_exists.side_effect = exists_side_effect
        mock_read.return_value = "buildPythonApplication something"

        self.assertTrue(cap.applies_to_layer("nix"))
        self.assertTrue(cap.is_provided(self.ctx, "nix"))

    @patch("pkgmgr.capabilities.os.path.exists", return_value=True)
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="install:\n\t echo 'installing'\n",
    )
    def test_make_install_makefile_layer(self, mock_file, mock_exists):
        cap = MakeInstallCapability()

        self.assertTrue(cap.applies_to_layer("makefile"))
        self.assertTrue(cap.is_provided(self.ctx, "makefile"))

    @patch("pkgmgr.capabilities.os.path.exists")
    def test_nix_flake_capability_on_nix_layer(self, mock_exists):
        cap = NixFlakeCapability()

        def exists_side_effect(path):
            return path.endswith("flake.nix")

        mock_exists.side_effect = exists_side_effect

        self.assertTrue(cap.applies_to_layer("nix"))
        self.assertTrue(cap.is_provided(self.ctx, "nix"))


if __name__ == "__main__":
    unittest.main()
