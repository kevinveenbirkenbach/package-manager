from __future__ import annotations

import json
import os
import shutil
from typing import Any, Dict, List

from pkgmgr.cli.context import CLIContext
from pkgmgr.cli.tools.paths import resolve_repository_path
from pkgmgr.core.command.run import run_command
from pkgmgr.core.repository.identifier import get_repo_identifier

Repository = Dict[str, Any]


def _ensure_vscode_cli_available() -> None:
    """
    Ensure that the VS Code CLI ('code') is available in PATH.
    """
    if shutil.which("code") is None:
        raise RuntimeError(
            "VS Code CLI ('code') not found in PATH.\n\n"
            "Hint:\n"
            "  Install Visual Studio Code and ensure the 'code' command is available.\n"
            "  VS Code → Command Palette → 'Shell Command: Install code command in PATH'\n"
        )


def _ensure_identifiers_are_filename_safe(identifiers: List[str]) -> None:
    """
    Ensure identifiers can be used in a filename.

    If an identifier contains '/', it likely means the repository has not yet
    been explicitly identified (no short identifier configured).
    """
    invalid = [i for i in identifiers if "/" in i or os.sep in i]
    if invalid:
        raise RuntimeError(
            "Cannot create VS Code workspace.\n\n"
            "The following repositories are not yet identified "
            "(identifier contains '/'): \n"
            + "\n".join(f"  - {i}" for i in invalid)
            + "\n\n"
            "Hint:\n"
            "  The repository has no short identifier yet.\n"
            "  Add an explicit identifier in your configuration before using `pkgmgr tools code`.\n"
        )


def _resolve_workspaces_dir(ctx: CLIContext) -> str:
    directories_cfg = ctx.config_merged.get("directories") or {}
    return os.path.expanduser(directories_cfg.get("workspaces", "~/Workspaces"))


def _build_workspace_filename(identifiers: List[str]) -> str:
    sorted_identifiers = sorted(identifiers)
    return "_".join(sorted_identifiers) + ".code-workspace"


def _build_workspace_data(
    selected: List[Repository], ctx: CLIContext
) -> Dict[str, Any]:
    folders = [{"path": resolve_repository_path(repo, ctx)} for repo in selected]
    return {
        "folders": folders,
        "settings": {},
    }


def open_vscode_workspace(ctx: CLIContext, selected: List[Repository]) -> None:
    """
    Create (if missing) and open a VS Code workspace for the selected repositories.

    Policy:
      - Fail with a clear error if VS Code CLI is missing.
      - Fail with a clear error if any repository identifier contains '/', because that
        indicates the repo has not been explicitly identified (no short identifier).
      - Do NOT auto-sanitize identifiers and do NOT create subfolders under workspaces.
    """
    if not selected:
        print("No repositories selected.")
        return

    _ensure_vscode_cli_available()

    identifiers = [get_repo_identifier(repo, ctx.all_repositories) for repo in selected]
    _ensure_identifiers_are_filename_safe(identifiers)

    workspaces_dir = _resolve_workspaces_dir(ctx)
    os.makedirs(workspaces_dir, exist_ok=True)

    workspace_name = _build_workspace_filename(identifiers)
    workspace_file = os.path.join(workspaces_dir, workspace_name)

    workspace_data = _build_workspace_data(selected, ctx)

    if not os.path.exists(workspace_file):
        with open(workspace_file, "w", encoding="utf-8") as f:
            json.dump(workspace_data, f, indent=4)
        print(f"Created workspace file: {workspace_file}")
    else:
        print(f"Using existing workspace file: {workspace_file}")

    run_command(f'code "{workspace_file}"')
