#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for pkgmgr.cli.commands.repos

We focus on the behaviour of:

  - _resolve_repository_directory(...)
  - handle_repos_command(...) for the "path" and "shell" commands

Goals:

  * "path" should:
      - print repo["directory"] if present
      - fall back to get_repo_dir(ctx.repositories_base_dir, repo) otherwise
      - handle "no selected repos" gracefully

  * "shell" should:
      - resolve the directory via _resolve_repository_directory(...)
      - call run_command(...) with cwd set to the resolved directory
"""

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import patch

from pkgmgr.cli.context import CLIContext
from pkgmgr.cli.commands.repos import handle_repos_command


Repository = Dict[str, Any]


class TestReposCommand(unittest.TestCase):
    def _make_ctx(self, repositories: List[Repository]) -> CLIContext:
        """
        Helper to build a minimal CLIContext for tests.
        """
        return CLIContext(
            config_merged={},
            repositories_base_dir="/base/dir",
            all_repositories=repositories,
            binaries_dir="/bin/dir",
            user_config_path="~/.config/pkgmgr/config.yaml",
        )

    # ------------------------------------------------------------------
    # "path" command tests
    # ------------------------------------------------------------------

    def test_path_uses_explicit_directory_if_present(self) -> None:
        """
        When repository["directory"] is present, handle_repos_command("path")
        should print this value directly without calling get_repo_dir().
        """
        repos: List[Repository] = [
            {
                "provider": "github.com",
                "account": "kevinveenbirkenbach",
                "repository": "package-manager",
                "directory": "/custom/path/pkgmgr",
            }
        ]
        ctx = self._make_ctx(repos)

        args = SimpleNamespace(
            command="path",
            preview=False,
            list=False,
            system=False,
            extra_args=[],
        )

        buf = io.StringIO()

        with patch(
            "pkgmgr.cli.commands.repos.get_repo_dir"
        ) as mock_get_repo_dir, redirect_stdout(buf):
            handle_repos_command(args, ctx, selected=repos)

        output = buf.getvalue().strip().splitlines()
        self.assertIn("/custom/path/pkgmgr", output)
        mock_get_repo_dir.assert_not_called()

    def test_path_falls_back_to_get_repo_dir_if_directory_missing(self) -> None:
        """
        When repository["directory"] is missing, handle_repos_command("path")
        should call get_repo_dir(ctx.repositories_base_dir, repo) and print
        the returned value.
        """
        repos: List[Repository] = [
            {
                "provider": "github.com",
                "account": "kevinveenbirkenbach",
                "repository": "package-manager",
            }
        ]
        ctx = self._make_ctx(repos)

        args = SimpleNamespace(
            command="path",
            preview=False,
            list=False,
            system=False,
            extra_args=[],
        )

        buf = io.StringIO()

        with patch(
            "pkgmgr.cli.commands.repos.get_repo_dir",
            return_value="/resolved/from/get_repo_dir",
        ) as mock_get_repo_dir, redirect_stdout(buf):
            handle_repos_command(args, ctx, selected=repos)

        output = buf.getvalue().strip().splitlines()
        self.assertIn("/resolved/from/get_repo_dir", output)
        mock_get_repo_dir.assert_called_once_with("/base/dir", repos[0])

    def test_path_with_no_selected_repos_prints_message(self) -> None:
        """
        When 'selected' is empty, the 'path' command should print a friendly
        message and not raise.
        """
        ctx = self._make_ctx(repositories=[])
        args = SimpleNamespace(
            command="path",
            preview=False,
            list=False,
            system=False,
            extra_args=[],
        )

        buf = io.StringIO()
        with redirect_stdout(buf):
            handle_repos_command(args, ctx, selected=[])

        output = buf.getvalue()
        self.assertIn("No repositories selected for path", output)

    # ------------------------------------------------------------------
    # "shell" command tests
    # ------------------------------------------------------------------

    def test_shell_resolves_directory_and_calls_run_command(self) -> None:
        """
        'shell' should resolve the repository directory and pass it as cwd
        to run_command(), along with the full shell command string.
        """
        repos: List[Repository] = [
            {
                "provider": "github.com",
                "account": "kevinveenbirkenbach",
                "repository": "package-manager",
            }
        ]
        ctx = self._make_ctx(repos)

        args = SimpleNamespace(
            command="shell",
            preview=False,
            shell_command=["echo", "hello"],
        )

        with patch(
            "pkgmgr.cli.commands.repos.get_repo_dir",
            return_value="/resolved/for/shell",
        ) as mock_get_repo_dir, patch(
            "pkgmgr.cli.commands.repos.run_command"
        ) as mock_run_command:
            buf = io.StringIO()
            with redirect_stdout(buf):
                handle_repos_command(args, ctx, selected=repos)

        # _resolve_repository_directory should have called get_repo_dir
        mock_get_repo_dir.assert_called_once_with("/base/dir", repos[0])

        # run_command should be invoked with cwd set to the resolved path
        mock_run_command.assert_called_once()
        called_args, called_kwargs = mock_run_command.call_args

        self.assertEqual("echo hello", called_args[0])        # command string
        self.assertEqual("/resolved/for/shell", called_kwargs["cwd"])
        self.assertFalse(called_kwargs["preview"])

    def test_shell_without_command_exits_with_error(self) -> None:
        """
        'shell' without -c/--command should print an error and exit with code 2.
        """
        repos: List[Repository] = []
        ctx = self._make_ctx(repos)

        args = SimpleNamespace(
            command="shell",
            preview=False,
            shell_command=[],
        )

        buf = io.StringIO()
        with redirect_stdout(buf), self.assertRaises(SystemExit) as cm:
            handle_repos_command(args, ctx, selected=repos)

        self.assertEqual(cm.exception.code, 2)
        output = buf.getvalue()
        self.assertIn("'shell' requires a command via -c/--command", output)


if __name__ == "__main__":
    unittest.main()
