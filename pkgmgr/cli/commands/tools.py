from __future__ import annotations

import json
import os

from typing import Any, Dict, List

from pkgmgr.cli.context import CLIContext
from pkgmgr.core.command.run import run_command
from pkgmgr.core.repository.identifier import get_repo_identifier


Repository = Dict[str, Any]


def handle_tools_command(
    args,
    ctx: CLIContext,
    selected: List[Repository],
) -> None:
    """
    Handle integration commands:
    - explore (file manager)
    - terminal (GNOME Terminal)
    - code (VS Code workspace)
    """

    # --------------------------------------------------------
    # explore
    # --------------------------------------------------------
    if args.command == "explore":
        for repository in selected:
            run_command(
                f"nautilus {repository['directory']} & disown"
            )
        return

    # --------------------------------------------------------
    # terminal
    # --------------------------------------------------------
    if args.command == "terminal":
        for repository in selected:
            run_command(
                f'gnome-terminal --tab --working-directory="{repository["directory"]}"'
            )
        return

    # --------------------------------------------------------
    # code
    # --------------------------------------------------------
    if args.command == "code":
        if not selected:
            print("No repositories selected.")
            return

        identifiers = [
            get_repo_identifier(repo, ctx.all_repositories)
            for repo in selected
        ]
        sorted_identifiers = sorted(identifiers)
        workspace_name = "_".join(sorted_identifiers) + ".code-workspace"

        workspaces_dir = os.path.expanduser(
            ctx.config_merged.get("directories").get("workspaces")
        )
        os.makedirs(workspaces_dir, exist_ok=True)
        workspace_file = os.path.join(workspaces_dir, workspace_name)

        folders = [{"path": repository["directory"]} for repository in selected]

        workspace_data = {
            "folders": folders,
            "settings": {},
        }
        if not os.path.exists(workspace_file):
            with open(workspace_file, "w") as f:
                json.dump(workspace_data, f, indent=4)
            print(f"Created workspace file: {workspace_file}")
        else:
            print(f"Using existing workspace file: {workspace_file}")

        run_command(f'code "{workspace_file}"')
        return
