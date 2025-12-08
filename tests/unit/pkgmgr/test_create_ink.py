# tests/unit/pkgmgr/test_create_ink.py

import unittest
from unittest.mock import patch

import pkgmgr.create_ink as create_ink_module


class TestCreateInk(unittest.TestCase):
    @patch("pkgmgr.create_ink.get_repo_dir")
    @patch("pkgmgr.create_ink.get_repo_identifier")
    def test_create_ink_skips_when_no_command(
        self,
        mock_get_repo_identifier,
        mock_get_repo_dir,
    ):
        repo = {}  # no 'command' key
        mock_get_repo_identifier.return_value = "test-id"
        mock_get_repo_dir.return_value = "/repos/test-id"

        with patch("pkgmgr.create_ink.os.makedirs") as mock_makedirs, \
             patch("pkgmgr.create_ink.os.symlink") as mock_symlink, \
             patch("pkgmgr.create_ink.os.chmod") as mock_chmod:
            create_ink_module.create_ink(
                repo=repo,
                repositories_base_dir="/repos",
                bin_dir="/bin",
                all_repos=[repo],
                quiet=True,
                preview=False,
            )

        mock_makedirs.assert_not_called()
        mock_symlink.assert_not_called()
        mock_chmod.assert_not_called()

    @patch("pkgmgr.create_ink.get_repo_dir")
    @patch("pkgmgr.create_ink.get_repo_identifier")
    def test_create_ink_preview_only(
        self,
        mock_get_repo_identifier,
        mock_get_repo_dir,
    ):
        repo = {"command": "/repos/test-id/main.py"}
        mock_get_repo_identifier.return_value = "test-id"
        mock_get_repo_dir.return_value = "/repos/test-id"

        with patch("pkgmgr.create_ink.os.makedirs") as mock_makedirs, \
             patch("pkgmgr.create_ink.os.symlink") as mock_symlink, \
             patch("pkgmgr.create_ink.os.chmod") as mock_chmod:
            create_ink_module.create_ink(
                repo=repo,
                repositories_base_dir="/repos",
                bin_dir="/bin",
                all_repos=[repo],
                quiet=True,
                preview=True,
            )

        mock_makedirs.assert_not_called()
        mock_symlink.assert_not_called()
        mock_chmod.assert_not_called()

    @patch("pkgmgr.create_ink.get_repo_dir")
    @patch("pkgmgr.create_ink.get_repo_identifier")
    def test_create_ink_creates_symlink_and_alias(
        self,
        mock_get_repo_identifier,
        mock_get_repo_dir,
    ):
        repo = {
            "command": "/repos/test-id/main.py",
            "alias": "alias-id",
        }
        mock_get_repo_identifier.return_value = "test-id"
        mock_get_repo_dir.return_value = "/repos/test-id"

        with patch("pkgmgr.create_ink.os.makedirs") as mock_makedirs, \
             patch("pkgmgr.create_ink.os.symlink") as mock_symlink, \
             patch("pkgmgr.create_ink.os.chmod") as mock_chmod, \
             patch("pkgmgr.create_ink.os.path.exists", return_value=False), \
             patch("pkgmgr.create_ink.os.path.islink", return_value=False), \
             patch("pkgmgr.create_ink.os.remove") as mock_remove, \
             patch("pkgmgr.create_ink.os.path.realpath", side_effect=lambda p: p):
            create_ink_module.create_ink(
                repo=repo,
                repositories_base_dir="/repos",
                bin_dir="/bin",
                all_repos=[repo],
                quiet=True,
                preview=False,
            )

        # main link + alias link
        self.assertEqual(mock_symlink.call_count, 2)
        mock_makedirs.assert_called_once()
        mock_chmod.assert_called_once()
        mock_remove.assert_not_called()


if __name__ == "__main__":
    unittest.main()
