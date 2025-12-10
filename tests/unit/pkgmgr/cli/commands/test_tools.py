from __future__ import annotations

import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from typing import Any, Dict, List

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
      - Correct path resolution for repositories that have a 'directory' key.
      - Correct shell commands for 'explore' and 'terminal'.
      - Proper workspace creation and invocation of 'code' for the 'code' command.
    """

    def setUp(self) -> None:
        # Two fake repositories with explicit 'directory' entries so that
        # _resolve_repository_path() does not need to call get_repo_dir().
        self.repos: List[Repository] = [
            {"alias": "repo1", "directory": "/tmp/repo1"},
            {"alias": "repo2", "directory": "/tmp/repo2"},
        ]

        # Minimal CLI context; only attributes used in tools.py are provided.
        self.ctx = SimpleNamespace(
            config_merged={"directories": {"workspaces": "~/Workspaces"}},
            all_repositories=self.repos,
            repositories_base_dir="/base/dir",
        )

    # ------------------------------------------------------------------ #
    # Helper
    # ------------------------------------------------------------------ #

    def _patch_run_command(self):
        """
        Convenience context manager for patching run_command in tools module.
        """
        from unittest.mock import patch

        return patch("pkgmgr.cli.commands.tools.run_command")

    # ------------------------------------------------------------------ #
    # Tests for 'explore'
    # ------------------------------------------------------------------ #

    def test_explore_uses_directory_paths(self) -> None:
        """
        The 'explore' command should call Nautilus with the resolved
        repository paths and use '& disown' as in the implementation.
        """
        from unittest.mock import call

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
        """
        The 'terminal' command should open a GNOME Terminal tab with the
        repository as its working directory.
        """
        from unittest.mock import call

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

    def test_code_creates_workspace_and_calls_code(self) -> None:
        """
        The 'code' command should:

          - Build a workspace file name from sorted repository identifiers.
          - Resolve the repository paths into VS Code 'folders'.
          - Create the workspace file if it does not exist.
          - Call 'code "<workspace_file>"' via run_command.
        """
        from unittest.mock import patch

        args = _Args(command="code")

        with tempfile.TemporaryDirectory() as tmpdir:
            # Patch expanduser so that the configured '~/Workspaces'
            # resolves into our temporary directory.
            with patch(
                "pkgmgr.cli.commands.tools.os.path.expanduser"
            ) as mock_expanduser:
                mock_expanduser.return_value = tmpdir

                # Patch get_repo_identifier so the resulting workspace file
                # name is deterministic and easy to assert.
                with patch(
                    "pkgmgr.cli.commands.tools.get_repo_identifier"
                ) as mock_get_identifier:
                    mock_get_identifier.side_effect = ["repo-b", "repo-a"]

                    with self._patch_run_command() as mock_run_command:
                        handle_tools_command(args, self.ctx, self.repos)

                    # The identifiers are ['repo-b', 'repo-a'], which are
                    # sorted to ['repo-a', 'repo-b'] and joined with '_'.
                    expected_workspace_name = "repo-a_repo-b.code-workspace"
                    expected_workspace_file = os.path.join(
                        tmpdir, expected_workspace_name
                    )

                    # Workspace file should have been created.
                    self.assertTrue(
                        os.path.exists(expected_workspace_file),
                        "Workspace file was not created.",
                    )

                    # The content of the workspace must be valid JSON with
                    # the expected folder paths.
                    with open(expected_workspace_file, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    self.assertIn("folders", data)
                    folder_paths = {f["path"] for f in data["folders"]}
                    self.assertEqual(
                        folder_paths,
                        {"/tmp/repo1", "/tmp/repo2"},
                    )

                    # And VS Code must have been invoked with that workspace.
                    mock_run_command.assert_called_once_with(
                        f'code "{expected_workspace_file}"'
                    )
