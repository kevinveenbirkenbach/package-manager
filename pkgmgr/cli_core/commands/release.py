from __future__ import annotations

import os
import sys
from typing import Any, Dict, List, Optional

from pkgmgr.cli_core.context import CLIContext
from pkgmgr.get_repo_dir import get_repo_dir
from pkgmgr import release as rel


Repository = Dict[str, Any]


def handle_release(
    args,
    ctx: CLIContext,
    selected: List[Repository],
) -> None:
    """
    Handle the 'release' command.

    Creates a release by incrementing the version and updating the changelog
    in the selected repositories.
    """

    if not selected:
        print("No repositories selected for release.")
        sys.exit(1)

    original_dir = os.getcwd()

    for repo in selected:
        repo_dir: Optional[str] = repo.get("directory")
        if not repo_dir:
            repo_dir = get_repo_dir(ctx.repositories_base_dir, repo)

        pyproject_path = os.path.join(repo_dir, "pyproject.toml")
        changelog_path = os.path.join(repo_dir, "CHANGELOG.md")

        print(
            f"Releasing repository '{repo.get('repository')}' in '{repo_dir}'..."
        )

        os.chdir(repo_dir)
        rel.release(
            pyproject_path=pyproject_path,
            changelog_path=changelog_path,
            release_type=args.release_type,
            message=args.message,
        )
        os.chdir(original_dir)
