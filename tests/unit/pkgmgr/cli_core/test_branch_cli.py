#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the `pkgmgr branch` CLI wiring.

These tests verify that:
  - The argument parser creates the correct structure for
    `branch open` and `branch close`.
  - `handle_branch` calls the corresponding helper functions
    with the expected arguments (including base branch and cwd).
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.cli_core.parser import create_parser
from pkgmgr.cli_core.commands.branch import handle_branch


class TestBranchCLI(unittest.TestCase):
    """
    Tests for the branch subcommands implemented in cli_core.
    """

    def _create_parser(self):
        """
        Create the top-level parser with a minimal description.
        """
        return create_parser("pkgmgr test parser")

    @patch("pkgmgr.cli_core.commands.branch.open_branch")
    def test_branch_open_with_name_and_base(self, mock_open_branch):
        """
        Ensure that `pkgmgr branch open <name> --base <branch>` calls
        open_branch() with the correct parameters.
        """
        parser = self._create_parser()
        args = parser.parse_args(
            ["branch", "open", "feature/test-branch", "--base", "develop"]
        )

        # Sanity check: parser wiring
        self.assertEqual(args.command, "branch")
        self.assertEqual(args.subcommand, "open")
        self.assertEqual(args.name, "feature/test-branch")
        self.assertEqual(args.base, "develop")

        # ctx is currently unused by handle_branch, so we can pass None
        handle_branch(args, ctx=None)

        mock_open_branch.assert_called_once()
        _args, kwargs = mock_open_branch.call_args

        self.assertEqual(kwargs.get("name"), "feature/test-branch")
        self.assertEqual(kwargs.get("base_branch"), "develop")
        self.assertEqual(kwargs.get("cwd"), ".")

    @patch("pkgmgr.cli_core.commands.branch.close_branch")
    def test_branch_close_with_name_and_base(self, mock_close_branch):
        """
        Ensure that `pkgmgr branch close <name> --base <branch>` calls
        close_branch() with the correct parameters.
        """
        parser = self._create_parser()
        args = parser.parse_args(
            ["branch", "close", "feature/old-branch", "--base", "main"]
        )

        # Sanity check: parser wiring
        self.assertEqual(args.command, "branch")
        self.assertEqual(args.subcommand, "close")
        self.assertEqual(args.name, "feature/old-branch")
        self.assertEqual(args.base, "main")

        handle_branch(args, ctx=None)

        mock_close_branch.assert_called_once()
        _args, kwargs = mock_close_branch.call_args

        self.assertEqual(kwargs.get("name"), "feature/old-branch")
        self.assertEqual(kwargs.get("base_branch"), "main")
        self.assertEqual(kwargs.get("cwd"), ".")

    @patch("pkgmgr.cli_core.commands.branch.close_branch")
    def test_branch_close_without_name_uses_none(self, mock_close_branch):
        """
        Ensure that `pkgmgr branch close` without a name passes name=None
        into close_branch(), leaving branch resolution to the helper.
        """
        parser = self._create_parser()
        args = parser.parse_args(["branch", "close"])

        # Parser wiring: no name → None
        self.assertEqual(args.command, "branch")
        self.assertEqual(args.subcommand, "close")
        self.assertIsNone(args.name)

        handle_branch(args, ctx=None)

        mock_close_branch.assert_called_once()
        _args, kwargs = mock_close_branch.call_args

        self.assertIsNone(kwargs.get("name"))
        self.assertEqual(kwargs.get("base_branch"), "main")
        self.assertEqual(kwargs.get("cwd"), ".")


if __name__ == "__main__":
    unittest.main()
