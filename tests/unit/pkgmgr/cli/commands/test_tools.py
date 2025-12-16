from __future__ import annotations

import unittest
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import call, patch

from pkgmgr.cli.commands.tools import handle_tools_command

Repository = Dict[str, Any]


class _Args:
    """
    Simple helper object to mimic argparse.Namespace for handle_tools_command.
    """

    def __init__(self, command: str) -> None:
        self.command = command


class TestHandleToolsCommand(unittest.TestCase):
    """
    Unit tests for pkgmgr.cli.commands.tools.handle_tools_command.

    We focus on:
      - Correct path resolution and shell commands for 'explore' and 'terminal'.
      - For 'code': delegation to pkgmgr.cli.tools.open_vscode_workspace.
    """

    def setUp(self) -> None:
        self.repos: List[Repository] = [
            {"alias": "repo1", "directory": "/tmp/repo1"},
            {"alias": "repo2", "directory": "/tmp/repo2"},
        ]

        self.ctx = SimpleNamespace(
            config_merged={"directories": {"workspaces": "~/Workspaces"}},
            all_repositories=self.repos,
            repositories_base_dir="/base/dir",
        )

    def _patch_run_command(self):
        return patch("pkgmgr.cli.commands.tools.run_command")

    # ------------------------------------------------------------------ #
    # Tests for 'explore'
    # ------------------------------------------------------------------ #

    def test_explore_uses_directory_paths(self) -> None:
        args = _Args(command="explore")

        with self._patch_run_command() as mock_run_command:
            handle_tools_command(args, self.ctx, self.repos)

        expected_calls = [
            call('nautilus "/tmp/repo1" & disown'),
            call('nautilus "/tmp/repo2" & disown'),
        ]
        self.assertEqual(mock_run_command.call_args_list, expected_calls)

    # ------------------------------------------------------------------ #
    # Tests for 'terminal'
    # ------------------------------------------------------------------ #

    def test_terminal_uses_directory_paths(self) -> None:
        args = _Args(command="terminal")

        with self._patch_run_command() as mock_run_command:
            handle_tools_command(args, self.ctx, self.repos)

        expected_calls = [
            call('gnome-terminal --tab --working-directory="/tmp/repo1"'),
            call('gnome-terminal --tab --working-directory="/tmp/repo2"'),
        ]
        self.assertEqual(mock_run_command.call_args_list, expected_calls)

    # ------------------------------------------------------------------ #
    # Tests for 'code'
    # ------------------------------------------------------------------ #

    def test_code_delegates_to_open_vscode_workspace(self) -> None:
        args = _Args(command="code")

        with patch("pkgmgr.cli.commands.tools.open_vscode_workspace") as m:
            handle_tools_command(args, self.ctx, self.repos)

        m.assert_called_once_with(self.ctx, self.repos)
