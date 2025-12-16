from __future__ import annotations

from typing import Any, Dict, List

from pkgmgr.cli.context import CLIContext
from pkgmgr.cli.tools import open_vscode_workspace
from pkgmgr.cli.tools.paths import resolve_repository_path
from pkgmgr.core.command.run import run_command

Repository = Dict[str, Any]


def handle_tools_command(
    args,
    ctx: CLIContext,
    selected: List[Repository],
) -> None:
    # ------------------------------------------------------------------
    # nautilus "explore" command
    # ------------------------------------------------------------------
    if args.command == "explore":
        for repository in selected:
            repo_path = resolve_repository_path(repository, ctx)
            run_command(f'nautilus "{repo_path}" & disown')
        return

    # ------------------------------------------------------------------
    # GNOME terminal command
    # ------------------------------------------------------------------
    if args.command == "terminal":
        for repository in selected:
            repo_path = resolve_repository_path(repository, ctx)
            run_command(f'gnome-terminal --tab --working-directory="{repo_path}"')
        return

    # ------------------------------------------------------------------
    # VS Code workspace command
    # ------------------------------------------------------------------
    if args.command == "code":
        open_vscode_workspace(ctx, selected)
        return
