from __future__ import annotations

import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest.mock import patch

Repository = Dict[str, Any]


class TestOpenVSCodeWorkspace(unittest.TestCase):
    def test_no_selected_repos_prints_message_and_returns(self) -> None:
        from pkgmgr.cli.tools.vscode import open_vscode_workspace

        ctx = SimpleNamespace(config_merged={}, all_repositories=[])

        with patch("builtins.print") as p:
            open_vscode_workspace(ctx, [])

        p.assert_called_once()
        self.assertIn("No repositories selected.", str(p.call_args[0][0]))

    def test_raises_if_code_cli_missing(self) -> None:
        from pkgmgr.cli.tools.vscode import open_vscode_workspace

        ctx = SimpleNamespace(config_merged={}, all_repositories=[])
        selected: List[Repository] = [
            {"provider": "github.com", "account": "x", "repository": "y"}
        ]

        with patch("pkgmgr.cli.tools.vscode.shutil.which", return_value=None):
            with self.assertRaises(RuntimeError) as cm:
                open_vscode_workspace(ctx, selected)

        self.assertIn("VS Code CLI ('code') not found", str(cm.exception))

    def test_raises_if_identifier_contains_slash(self) -> None:
        from pkgmgr.cli.tools.vscode import open_vscode_workspace

        ctx = SimpleNamespace(
            config_merged={"directories": {"workspaces": "~/Workspaces"}},
            all_repositories=[],
        )
        selected: List[Repository] = [
            {"provider": "github.com", "account": "x", "repository": "y"}
        ]

        with (
            patch("pkgmgr.cli.tools.vscode.shutil.which", return_value="/usr/bin/code"),
            patch(
                "pkgmgr.cli.tools.vscode.get_repo_identifier",
                return_value="github.com/x/y",
            ),
        ):
            with self.assertRaises(RuntimeError) as cm:
                open_vscode_workspace(ctx, selected)

        msg = str(cm.exception)
        self.assertIn("not yet identified", msg)
        self.assertIn("identifier contains '/'", msg)

    def test_creates_workspace_file_and_calls_code(self) -> None:
        from pkgmgr.cli.tools.vscode import open_vscode_workspace

        with tempfile.TemporaryDirectory() as tmp:
            workspaces_dir = os.path.join(tmp, "Workspaces")
            repo_path = os.path.join(tmp, "Repos", "dotlinker")

            ctx = SimpleNamespace(
                config_merged={"directories": {"workspaces": workspaces_dir}},
                all_repositories=[],
                repositories_base_dir=os.path.join(tmp, "Repos"),
            )
            selected: List[Repository] = [
                {
                    "provider": "github.com",
                    "account": "kevin",
                    "repository": "dotlinker",
                }
            ]

            with (
                patch(
                    "pkgmgr.cli.tools.vscode.shutil.which", return_value="/usr/bin/code"
                ),
                patch(
                    "pkgmgr.cli.tools.vscode.get_repo_identifier",
                    return_value="dotlinker",
                ),
                patch(
                    "pkgmgr.cli.tools.vscode.resolve_repository_path",
                    return_value=repo_path,
                ),
                patch("pkgmgr.cli.tools.vscode.run_command") as run_cmd,
            ):
                open_vscode_workspace(ctx, selected)

            workspace_file = os.path.join(workspaces_dir, "dotlinker.code-workspace")
            self.assertTrue(os.path.exists(workspace_file))

            with open(workspace_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertEqual(data["folders"], [{"path": repo_path}])
            self.assertEqual(data["settings"], {})

            run_cmd.assert_called_once_with(f'code "{workspace_file}"')

    def test_uses_existing_workspace_file_without_overwriting(self) -> None:
        from pkgmgr.cli.tools.vscode import open_vscode_workspace

        with tempfile.TemporaryDirectory() as tmp:
            workspaces_dir = os.path.join(tmp, "Workspaces")
            os.makedirs(workspaces_dir, exist_ok=True)

            workspace_file = os.path.join(workspaces_dir, "dotlinker.code-workspace")
            original = {"folders": [{"path": "/original"}], "settings": {"x": 1}}
            with open(workspace_file, "w", encoding="utf-8") as f:
                json.dump(original, f)

            ctx = SimpleNamespace(
                config_merged={"directories": {"workspaces": workspaces_dir}},
                all_repositories=[],
            )
            selected: List[Repository] = [
                {
                    "provider": "github.com",
                    "account": "kevin",
                    "repository": "dotlinker",
                }
            ]

            with (
                patch(
                    "pkgmgr.cli.tools.vscode.shutil.which", return_value="/usr/bin/code"
                ),
                patch(
                    "pkgmgr.cli.tools.vscode.get_repo_identifier",
                    return_value="dotlinker",
                ),
                patch(
                    "pkgmgr.cli.tools.vscode.resolve_repository_path",
                    return_value="/new/path",
                ),
                patch("pkgmgr.cli.tools.vscode.run_command") as run_cmd,
            ):
                open_vscode_workspace(ctx, selected)

            with open(workspace_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertEqual(data, original)
            run_cmd.assert_called_once_with(f'code "{workspace_file}"')
