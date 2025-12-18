#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for pkgmgr.cli.commands.release.

These tests focus on the wiring layer:
  - Argument handling for the release command as defined by the
    top-level parser (cli.parser.create_parser).
  - Correct invocation of pkgmgr.actions.release.release(...) for the
    selected repositories.
  - Behaviour of --preview, --list, --close, and -f/--force.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import List
from unittest.mock import patch, call

import argparse
import unittest


class TestReleaseCommand(unittest.TestCase):
    """
    Tests for the `pkgmgr release` CLI wiring.
    """

    def _make_ctx(self, all_repos: List[dict]) -> SimpleNamespace:
        """
        Create a minimal CLIContext-like object for tests.

        Only the attributes that handle_release() uses are provided.
        """
        return SimpleNamespace(
            config_merged={},
            repositories_base_dir="/base/dir",
            all_repositories=all_repos,
            binaries_dir="/bin",
            user_config_path="/tmp/config.yaml",
        )

    def _parse_release_args(self, argv: List[str]) -> argparse.Namespace:
        """
        Build a real top-level parser and parse the given argv list
        to obtain the Namespace for the `release` command.
        """
        from pkgmgr.cli.parser import create_parser

        parser = create_parser("test parser")
        args = parser.parse_args(argv)
        self.assertEqual(args.command, "release")
        return args

    @patch("pkgmgr.cli.commands.release.os.path.isdir", return_value=True)
    @patch("pkgmgr.cli.commands.release.run_release")
    @patch("pkgmgr.cli.commands.release.get_repo_dir")
    @patch("pkgmgr.cli.commands.release.get_repo_identifier")
    @patch("pkgmgr.cli.commands.release.os.chdir")
    @patch("pkgmgr.cli.commands.release.os.getcwd", return_value="/cwd")
    def test_release_with_close_and_message(
        self,
        mock_getcwd,
        mock_chdir,
        mock_get_repo_identifier,
        mock_get_repo_dir,
        mock_run_release,
        mock_isdir,
    ) -> None:
        """
        The release handler should call pkgmgr.actions.release.release() with:
          - release_type (e.g. minor)
          - provided message
          - preview flag
          - force flag
          - close flag

        It must change into the repository directory and then back.
        """
        from pkgmgr.cli.commands.release import handle_release

        repo = {"name": "dummy-repo"}
        selected = [repo]
        ctx = self._make_ctx(selected)

        mock_get_repo_identifier.return_value = "dummy-id"
        mock_get_repo_dir.return_value = "/repos/dummy"

        argv = [
            "release",
            "minor",
            "dummy-id",
            "-m",
            "Close branch after minor release",
            "--close",
            "-f",
        ]
        args = self._parse_release_args(argv)

        handle_release(args, ctx, selected)

        # We should have changed into the repo dir and then back.
        mock_chdir.assert_has_calls([call("/repos/dummy"), call("/cwd")])

        # And run_release should be invoked once with the expected parameters.
        mock_run_release.assert_called_once_with(
            pyproject_path="pyproject.toml",
            changelog_path="CHANGELOG.md",
            release_type="minor",
            message="Close branch after minor release",
            preview=False,
            force=True,
            close=True,
        )

    @patch("pkgmgr.cli.commands.release.os.path.isdir", return_value=True)
    @patch("pkgmgr.cli.commands.release.run_release")
    @patch("pkgmgr.cli.commands.release.get_repo_dir")
    @patch("pkgmgr.cli.commands.release.get_repo_identifier")
    @patch("pkgmgr.cli.commands.release.os.chdir")
    @patch("pkgmgr.cli.commands.release.os.getcwd", return_value="/cwd")
    def test_release_preview_mode(
        self,
        mock_getcwd,
        mock_chdir,
        mock_get_repo_identifier,
        mock_get_repo_dir,
        mock_run_release,
        mock_isdir,
    ) -> None:
        """
        In preview mode, the handler should pass preview=True to the
        release helper and force=False by default.
        """
        from pkgmgr.cli.commands.release import handle_release

        repo = {"name": "dummy-repo"}
        selected = [repo]
        ctx = self._make_ctx(selected)

        mock_get_repo_identifier.return_value = "dummy-id"
        mock_get_repo_dir.return_value = "/repos/dummy"

        argv = [
            "release",
            "patch",
            "dummy-id",
            "--preview",
        ]
        args = self._parse_release_args(argv)

        handle_release(args, ctx, selected)

        mock_run_release.assert_called_once_with(
            pyproject_path="pyproject.toml",
            changelog_path="CHANGELOG.md",
            release_type="patch",
            message=None,
            preview=True,
            force=False,
            close=False,
        )

    @patch("pkgmgr.cli.commands.release.run_release")
    @patch("pkgmgr.cli.commands.release.get_repo_dir")
    @patch("pkgmgr.cli.commands.release.get_repo_identifier")
    def test_release_list_mode_does_not_invoke_helper(
        self,
        mock_get_repo_identifier,
        mock_get_repo_dir,
        mock_run_release,
    ) -> None:
        """
        When --list is provided, the handler should print the list of affected
        repositories and must NOT invoke run_release().
        """
        from pkgmgr.cli.commands.release import handle_release

        repo1 = {"name": "repo-1"}
        repo2 = {"name": "repo-2"}
        selected = [repo1, repo2]
        ctx = self._make_ctx(selected)

        mock_get_repo_identifier.side_effect = ["id-1", "id-2"]

        argv = [
            "release",
            "major",
            "--list",
        ]
        args = self._parse_release_args(argv)

        handle_release(args, ctx, selected)

        mock_run_release.assert_not_called()
        self.assertEqual(
            mock_get_repo_identifier.call_args_list,
            [call(repo1, selected), call(repo2, selected)],
        )


if __name__ == "__main__":
    unittest.main()
