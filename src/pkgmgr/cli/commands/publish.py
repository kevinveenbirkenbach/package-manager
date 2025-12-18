from __future__ import annotations

import os
from typing import Any, Dict, List

from pkgmgr.actions.publish import publish
from pkgmgr.cli.context import CLIContext
from pkgmgr.core.repository.dir import get_repo_dir
from pkgmgr.core.repository.identifier import get_repo_identifier

Repository = Dict[str, Any]


def handle_publish(args, ctx: CLIContext, selected: List[Repository]) -> None:
    if not selected:
        print("[pkgmgr] No repositories selected for publish.")
        return

    for repo in selected:
        identifier = get_repo_identifier(repo, ctx.all_repositories)
        repo_dir = repo.get("directory") or get_repo_dir(
            ctx.repositories_base_dir, repo
        )

        if not os.path.isdir(repo_dir):
            print(f"[WARN] Skipping {identifier}: directory missing.")
            continue

        print(f"[pkgmgr] Publishing repository {identifier}...")
        publish(
            repo=repo,
            repo_dir=repo_dir,
            preview=getattr(args, "preview", False),
            interactive=not getattr(args, "non_interactive", False),
            allow_prompt=not getattr(args, "non_interactive", False),
        )
