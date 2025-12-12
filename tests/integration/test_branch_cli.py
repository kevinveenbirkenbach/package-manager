#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for the `pkgmgr branch` CLI wiring.

These tests verify that:
  - The argument parser creates the correct structure for
    `branch open`, `branch close` and `branch drop`.
  - `handle_branch` calls the corresponding helper functions
    with the expected arguments (including base branch, cwd and force).
"""

from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.cli.parser import create_parser
from pkgmgr.cli.commands.branch import handle_branch


class TestBranchCLI(unittest.TestCase):
    """
    Tests for the branch subcommands implemented in the CLI.
    """

    def _create_parser(self):
        """
        Create the top-level parser with a minimal description.
        """
        return create_parser("pkgmgr test parser")

    # --------------------------------------------------------------------- #
    # branch open
    # --------------------------------------------------------------------- #

    @patch("pkgmgr.cli.commands.branch.open_branch")
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

    @patch("pkgmgr.cli.commands.branch.open_branch")
    def test_branch_open_with_name_and_default_base(self, mock_open_branch):
        """
        Ensure that `pkgmgr branch open <name>` without --base uses
        the default base branch 'main'.
        """
        parser = self._create_parser()
        args = parser.parse_args(["branch", "open", "feature/default-base"])

        self.assertEqual(args.command, "branch")
        self.assertEqual(args.subcommand, "open")
        self.assertEqual(args.name, "feature/default-base")
        self.assertEqual(args.base, "main")

        handle_branch(args, ctx=None)

        mock_open_branch.assert_called_once()
        _args, kwargs = mock_open_branch.call_args

        self.assertEqual(kwargs.get("name"), "feature/default-base")
        self.assertEqual(kwargs.get("base_branch"), "main")
        self.assertEqual(kwargs.get("cwd"), ".")

    # --------------------------------------------------------------------- #
    # branch close
    # --------------------------------------------------------------------- #

    @patch("pkgmgr.cli.commands.branch.close_branch")
    def test_branch_close_with_name_and_base(self, mock_close_branch):
        """
        Ensure that `pkgmgr branch close <name> --base <branch>` calls
        close_branch() with the correct parameters and force=False by default.
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
        self.assertFalse(args.force)

        handle_branch(args, ctx=None)

        mock_close_branch.assert_called_once()
        _args, kwargs = mock_close_branch.call_args

        self.assertEqual(kwargs.get("name"), "feature/old-branch")
        self.assertEqual(kwargs.get("base_branch"), "main")
        self.assertEqual(kwargs.get("cwd"), ".")
        self.assertFalse(kwargs.get("force"))

    @patch("pkgmgr.cli.commands.branch.close_branch")
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
        self.assertEqual(args.base, "main")
        self.assertFalse(args.force)

        handle_branch(args, ctx=None)

        mock_close_branch.assert_called_once()
        _args, kwargs = mock_close_branch.call_args

        self.assertIsNone(kwargs.get("name"))
        self.assertEqual(kwargs.get("base_branch"), "main")
        self.assertEqual(kwargs.get("cwd"), ".")
        self.assertFalse(kwargs.get("force"))

    @patch("pkgmgr.cli.commands.branch.close_branch")
    def test_branch_close_with_force(self, mock_close_branch):
        """
        Ensure that `pkgmgr branch close <name> --force` passes force=True.
        """
        parser = self._create_parser()
        args = parser.parse_args(
            ["branch", "close", "feature/old-branch", "--base", "main", "--force"]
        )

        self.assertTrue(args.force)

        handle_branch(args, ctx=None)

        mock_close_branch.assert_called_once()
        _args, kwargs = mock_close_branch.call_args

        self.assertEqual(kwargs.get("name"), "feature/old-branch")
        self.assertEqual(kwargs.get("base_branch"), "main")
        self.assertEqual(kwargs.get("cwd"), ".")
        self.assertTrue(kwargs.get("force"))

    # --------------------------------------------------------------------- #
    # branch drop
    # --------------------------------------------------------------------- #

    @patch("pkgmgr.cli.commands.branch.drop_branch")
    def test_branch_drop_with_name_and_base(self, mock_drop_branch):
        """
        Ensure that `pkgmgr branch drop <name> --base <branch>` calls
        drop_branch() with the correct parameters and force=False by default.
        """
        parser = self._create_parser()
        args = parser.parse_args(
            ["branch", "drop", "feature/tmp-branch", "--base", "develop"]
        )

        self.assertEqual(args.command, "branch")
        self.assertEqual(args.subcommand, "drop")
        self.assertEqual(args.name, "feature/tmp-branch")
        self.assertEqual(args.base, "develop")
        self.assertFalse(args.force)

        handle_branch(args, ctx=None)

        mock_drop_branch.assert_called_once()
        _args, kwargs = mock_drop_branch.call_args

        self.assertEqual(kwargs.get("name"), "feature/tmp-branch")
        self.assertEqual(kwargs.get("base_branch"), "develop")
        self.assertEqual(kwargs.get("cwd"), ".")
        self.assertFalse(kwargs.get("force"))

    @patch("pkgmgr.cli.commands.branch.drop_branch")
    def test_branch_drop_without_name(self, mock_drop_branch):
        """
        Ensure that `pkgmgr branch drop` without a name passes name=None
        into drop_branch(), leaving branch resolution to the helper.
        """
        parser = self._create_parser()
        args = parser.parse_args(["branch", "drop"])

        self.assertEqual(args.command, "branch")
        self.assertEqual(args.subcommand, "drop")
        self.assertIsNone(args.name)
        self.assertEqual(args.base, "main")
        self.assertFalse(args.force)

        handle_branch(args, ctx=None)

        mock_drop_branch.assert_called_once()
        _args, kwargs = mock_drop_branch.call_args

        self.assertIsNone(kwargs.get("name"))
        self.assertEqual(kwargs.get("base_branch"), "main")
        self.assertEqual(kwargs.get("cwd"), ".")
        self.assertFalse(kwargs.get("force"))

    @patch("pkgmgr.cli.commands.branch.drop_branch")
    def test_branch_drop_with_force(self, mock_drop_branch):
        """
        Ensure that `pkgmgr branch drop <name> --force` passes force=True.
        """
        parser = self._create_parser()
        args = parser.parse_args(
            ["branch", "drop", "feature/tmp-branch", "--force"]
        )

        self.assertTrue(args.force)

        handle_branch(args, ctx=None)

        mock_drop_branch.assert_called_once()
        _args, kwargs = mock_drop_branch.call_args

        self.assertEqual(kwargs.get("name"), "feature/tmp-branch")
        self.assertEqual(kwargs.get("base_branch"), "main")
        self.assertEqual(kwargs.get("cwd"), ".")
        self.assertTrue(kwargs.get("force"))


if __name__ == "__main__":
    unittest.main()
