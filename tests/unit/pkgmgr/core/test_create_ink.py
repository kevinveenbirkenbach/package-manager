#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import patch

import pkgmgr.core.command.ink as create_ink_module


class TestCreateInk(unittest.TestCase):
    @patch("pkgmgr.core.command.ink.get_repo_dir")
    @patch("pkgmgr.core.command.ink.get_repo_identifier")
    def test_create_ink_skips_when_no_command(
        self,
        mock_get_repo_identifier,
        mock_get_repo_dir,
    ):
        repo = {"name": "test-repo", "command": None}
        mock_get_repo_identifier.return_value = "test-id"
        mock_get_repo_dir.return_value = "/repos/test-id"

        with patch("pkgmgr.core.command.ink.os.makedirs") as mock_makedirs, \
             patch("pkgmgr.core.command.ink.os.symlink") as mock_symlink, \
             patch("pkgmgr.core.command.ink.os.chmod") as mock_chmod:
            create_ink_module.create_ink(
                repo=repo,
                repositories_base_dir="/repos",
                bin_dir="/bin",
                all_repos=[repo],
                preview=False,
            )

        mock_makedirs.assert_not_called()
        mock_symlink.assert_not_called()
        mock_chmod.assert_not_called()

    @patch("pkgmgr.core.command.ink.get_repo_dir")
    @patch("pkgmgr.core.command.ink.get_repo_identifier")
    def test_create_ink_preview_only(
        self,
        mock_get_repo_identifier,
        mock_get_repo_dir,
    ):
        repo = {"name": "test-repo", "command": "repo-cmd"}
        mock_get_repo_identifier.return_value = "test-id"
        mock_get_repo_dir.return_value = "/repos/test-id"

        with patch("pkgmgr.core.command.ink.os.makedirs") as mock_makedirs, \
             patch("pkgmgr.core.command.ink.os.symlink") as mock_symlink, \
             patch("pkgmgr.core.command.ink.os.chmod") as mock_chmod:
            create_ink_module.create_ink(
                repo=repo,
                repositories_base_dir="/repos",
                bin_dir="/bin",
                all_repos=[repo],
                preview=True,
            )

        mock_makedirs.assert_not_called()
        mock_symlink.assert_not_called()
        mock_chmod.assert_not_called()

    @patch("pkgmgr.core.command.ink.get_repo_dir")
    @patch("pkgmgr.core.command.ink.get_repo_identifier")
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

        with patch("pkgmgr.core.command.ink.os.makedirs") as mock_makedirs, \
             patch("pkgmgr.core.command.ink.os.symlink") as mock_symlink, \
             patch("pkgmgr.core.command.ink.os.chmod") as mock_chmod, \
             patch("pkgmgr.core.command.ink.os.path.exists", return_value=False), \
             patch("pkgmgr.core.command.ink.os.path.islink", return_value=False), \
             patch("pkgmgr.core.command.ink.os.path.realpath", side_effect=lambda p: p):
            create_ink_module.create_ink(
                repo=repo,
                repositories_base_dir="/repos",
                bin_dir="/bin",
                all_repos=[repo],
                preview=False,
            )

        # main link + alias link
        self.assertEqual(mock_symlink.call_count, 2)
        mock_makedirs.assert_called_once()
        mock_chmod.assert_called_once()

if __name__ == "__main__":
    unittest.main()
