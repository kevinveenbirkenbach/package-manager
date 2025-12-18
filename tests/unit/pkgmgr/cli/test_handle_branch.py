from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pkgmgr.cli.commands.branch import handle_branch
from pkgmgr.cli.context import CLIContext


class TestCliBranch(unittest.TestCase):
    def _dummy_ctx(self) -> CLIContext:
        """
        Minimal CLIContext; handle_branch does not actually use it,
        but we keep the type consistent.
        """
        return CLIContext(
            config_merged={},
            repositories_base_dir="/tmp/repos",
            all_repositories=[],
            binaries_dir="/tmp/bin",
            user_config_path="/tmp/config.yaml",
        )

    # ------------------------------------------------------------------
    # open subcommand
    # ------------------------------------------------------------------

    @patch("pkgmgr.cli.commands.branch.open_branch")
    def test_handle_branch_open_forwards_args_to_open_branch(
        self, mock_open_branch
    ) -> None:
        """
        handle_branch('open') should call open_branch with name, base and cwd='.'.
        """
        args = SimpleNamespace(
            command="branch",
            subcommand="open",
            name="feature/cli-test",
            base="develop",
        )

        ctx = self._dummy_ctx()

        handle_branch(args, ctx)

        mock_open_branch.assert_called_once()
        call_args, call_kwargs = mock_open_branch.call_args
        self.assertEqual(call_kwargs.get("name"), "feature/cli-test")
        self.assertEqual(call_kwargs.get("base_branch"), "develop")
        self.assertEqual(call_kwargs.get("cwd"), ".")

    @patch("pkgmgr.cli.commands.branch.open_branch")
    def test_handle_branch_open_uses_default_base_when_not_set(
        self, mock_open_branch
    ) -> None:
        """
        If --base is not passed, argparse gives base='main' (default),
        and handle_branch should propagate that to open_branch.
        """
        args = SimpleNamespace(
            command="branch",
            subcommand="open",
            name=None,
            base="main",
        )

        ctx = self._dummy_ctx()
        handle_branch(args, ctx)

        mock_open_branch.assert_called_once()
        _, call_kwargs = mock_open_branch.call_args
        self.assertIsNone(call_kwargs.get("name"))
        self.assertEqual(call_kwargs.get("base_branch"), "main")
        self.assertEqual(call_kwargs.get("cwd"), ".")

    # ------------------------------------------------------------------
    # close subcommand
    # ------------------------------------------------------------------

    @patch("pkgmgr.cli.commands.branch.close_branch")
    def test_handle_branch_close_forwards_args_to_close_branch(
        self, mock_close_branch
    ) -> None:
        """
        handle_branch('close') should call close_branch with name, base,
        cwd='.' and force=False by default.
        """
        args = SimpleNamespace(
            command="branch",
            subcommand="close",
            name="feature/cli-close",
            base="develop",
            force=False,
        )

        ctx = self._dummy_ctx()

        handle_branch(args, ctx)

        mock_close_branch.assert_called_once()
        _, call_kwargs = mock_close_branch.call_args
        self.assertEqual(call_kwargs.get("name"), "feature/cli-close")
        self.assertEqual(call_kwargs.get("base_branch"), "develop")
        self.assertEqual(call_kwargs.get("cwd"), ".")
        self.assertFalse(call_kwargs.get("force"))

    @patch("pkgmgr.cli.commands.branch.close_branch")
    def test_handle_branch_close_uses_default_base_when_not_set(
        self, mock_close_branch
    ) -> None:
        """
        If --base is not passed for 'close', argparse gives base='main'
        (default), and handle_branch should propagate that to close_branch.
        """
        args = SimpleNamespace(
            command="branch",
            subcommand="close",
            name=None,
            base="main",
            force=False,
        )

        ctx = self._dummy_ctx()

        handle_branch(args, ctx)

        mock_close_branch.assert_called_once()
        _, call_kwargs = mock_close_branch.call_args
        self.assertIsNone(call_kwargs.get("name"))
        self.assertEqual(call_kwargs.get("base_branch"), "main")
        self.assertEqual(call_kwargs.get("cwd"), ".")
        self.assertFalse(call_kwargs.get("force"))

    @patch("pkgmgr.cli.commands.branch.close_branch")
    def test_handle_branch_close_with_force_true(self, mock_close_branch) -> None:
        """
        handle_branch('close') should pass force=True when the args specify it.
        """
        args = SimpleNamespace(
            command="branch",
            subcommand="close",
            name="feature/cli-close-force",
            base="main",
            force=True,
        )

        ctx = self._dummy_ctx()

        handle_branch(args, ctx)

        mock_close_branch.assert_called_once()
        _, call_kwargs = mock_close_branch.call_args
        self.assertEqual(call_kwargs.get("name"), "feature/cli-close-force")
        self.assertEqual(call_kwargs.get("base_branch"), "main")
        self.assertEqual(call_kwargs.get("cwd"), ".")
        self.assertTrue(call_kwargs.get("force"))

    # ------------------------------------------------------------------
    # drop subcommand
    # ------------------------------------------------------------------

    @patch("pkgmgr.cli.commands.branch.drop_branch")
    def test_handle_branch_drop_forwards_args_to_drop_branch(
        self, mock_drop_branch
    ) -> None:
        """
        handle_branch('drop') should call drop_branch with name, base,
        cwd='.' and force=False by default.
        """
        args = SimpleNamespace(
            command="branch",
            subcommand="drop",
            name="feature/cli-drop",
            base="develop",
            force=False,
        )

        ctx = self._dummy_ctx()

        handle_branch(args, ctx)

        mock_drop_branch.assert_called_once()
        _, call_kwargs = mock_drop_branch.call_args
        self.assertEqual(call_kwargs.get("name"), "feature/cli-drop")
        self.assertEqual(call_kwargs.get("base_branch"), "develop")
        self.assertEqual(call_kwargs.get("cwd"), ".")
        self.assertFalse(call_kwargs.get("force"))

    @patch("pkgmgr.cli.commands.branch.drop_branch")
    def test_handle_branch_drop_uses_default_base_when_not_set(
        self, mock_drop_branch
    ) -> None:
        """
        If --base is not passed for 'drop', argparse gives base='main'
        (default), and handle_branch should propagate that to drop_branch.
        """
        args = SimpleNamespace(
            command="branch",
            subcommand="drop",
            name=None,
            base="main",
            force=False,
        )

        ctx = self._dummy_ctx()

        handle_branch(args, ctx)

        mock_drop_branch.assert_called_once()
        _, call_kwargs = mock_drop_branch.call_args
        self.assertIsNone(call_kwargs.get("name"))
        self.assertEqual(call_kwargs.get("base_branch"), "main")
        self.assertEqual(call_kwargs.get("cwd"), ".")
        self.assertFalse(call_kwargs.get("force"))

    @patch("pkgmgr.cli.commands.branch.drop_branch")
    def test_handle_branch_drop_with_force_true(self, mock_drop_branch) -> None:
        """
        handle_branch('drop') should pass force=True when the args specify it.
        """
        args = SimpleNamespace(
            command="branch",
            subcommand="drop",
            name="feature/cli-drop-force",
            base="main",
            force=True,
        )

        ctx = self._dummy_ctx()

        handle_branch(args, ctx)

        mock_drop_branch.assert_called_once()
        _, call_kwargs = mock_drop_branch.call_args
        self.assertEqual(call_kwargs.get("name"), "feature/cli-drop-force")
        self.assertEqual(call_kwargs.get("base_branch"), "main")
        self.assertEqual(call_kwargs.get("cwd"), ".")
        self.assertTrue(call_kwargs.get("force"))

    # ------------------------------------------------------------------
    # unknown subcommand
    # ------------------------------------------------------------------

    def test_handle_branch_unknown_subcommand_exits_with_code_2(self) -> None:
        """
        Unknown branch subcommand should result in SystemExit(2).
        """
        args = SimpleNamespace(
            command="branch",
            subcommand="unknown",
        )
        ctx = self._dummy_ctx()

        with self.assertRaises(SystemExit) as cm:
            handle_branch(args, ctx)

        self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
