from __future__ import annotations 

import json 
import os 

from typing import Any, Dict, List 

from pkgmgr .cli .context import CLIContext 
from pkgmgr .core .command .run import run_command 
from pkgmgr .core .repository .identifier import get_repo_identifier 
from pkgmgr .core .repository .dir import get_repo_dir 


Repository = Dict[str, Any]


def _resolve_repository_path(repository: Repository, ctx: CLIContext) -> str:
    """
    Resolve the filesystem path for a repository.

    Priority:
      1. Use explicit keys if present (directory / path / workspace / workspace_dir).
      2. Fallback to get_repo_dir(...) using the repositories base directory
         from the CLI context.
    """

    # 1) Explicit path-like keys on the repository object
    for key in ("directory", "path", "workspace", "workspace_dir"):
        value = repository.get(key)
        if value:
            return value

    # 2) Fallback: compute from base dir + repository metadata
    base_dir = (
        getattr(ctx, "repositories_base_dir", None)
        or getattr(ctx, "repositories_dir", None)
    )
    if not base_dir:
        raise RuntimeError(
            "Cannot resolve repositories base directory from context; "
            "expected ctx.repositories_base_dir or ctx.repositories_dir."
        )

    return get_repo_dir(base_dir, repository)


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
            repo_path = _resolve_repository_path(repository, ctx)
            run_command(
                f'nautilus "{repo_path}" & disown'
            )
        return 

    # ------------------------------------------------------------------
    # GNOME terminal command
    # ------------------------------------------------------------------
    if args.command == "terminal":
        for repository in selected:
            repo_path = _resolve_repository_path(repository, ctx)
            run_command(
                f'gnome-terminal --tab --working-directory="{repo_path}"'
            )
        return 

    # ------------------------------------------------------------------
    # VS Code workspace command
    # ------------------------------------------------------------------
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

        directories_cfg = ctx.config_merged.get("directories") or {}
        workspaces_dir = os.path.expanduser(
            directories_cfg.get("workspaces", "~/Workspaces")
        )
        os.makedirs(workspaces_dir, exist_ok=True)
        workspace_file = os.path.join(workspaces_dir, workspace_name)

        folders = [
            {"path": _resolve_repository_path(repository, ctx)}
            for repository in selected
        ]

        workspace_data = {
            "folders": folders,
            "settings": {},
        }

        if not os.path.exists(workspace_file):
            with open(workspace_file, "w", encoding="utf-8") as f:
                json.dump(workspace_data, f, indent=4)
            print(f"Created workspace file: {workspace_file}")
        else:
            print(f"Using existing workspace file: {workspace_file}")

        run_command(f'code "{workspace_file}"')
        return
