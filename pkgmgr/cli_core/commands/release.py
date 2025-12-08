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
    in a single selected repository.

    Important:
      - Releases are strictly limited to exactly ONE repository.
      - Using --all or specifying multiple identifiers for release does
        not make sense and is therefore rejected.
      - The --preview flag is respected and passed through to the release
        implementation so that no changes are made in preview mode.
    """

    if not selected:
        print("No repositories selected for release.")
        sys.exit(1)

    if len(selected) > 1:
        print(
            "[ERROR] Release operations are limited to a single repository.\n"
            "Do not use --all or multiple identifiers with 'pkgmgr release'."
        )
        sys.exit(1)

    original_dir = os.getcwd()

    repo = selected[0]

    repo_dir: Optional[str] = repo.get("directory")
    if not repo_dir:
        repo_dir = get_repo_dir(ctx.repositories_base_dir, repo)

    if not os.path.isdir(repo_dir):
        print(
            f"[ERROR] Repository directory does not exist locally: {repo_dir}"
        )
        sys.exit(1)

    pyproject_path = os.path.join(repo_dir, "pyproject.toml")
    changelog_path = os.path.join(repo_dir, "CHANGELOG.md")

    print(
        f"Releasing repository '{repo.get('repository')}' in '{repo_dir}'..."
    )

    os.chdir(repo_dir)
    try:
        rel.release(
            pyproject_path=pyproject_path,
            changelog_path=changelog_path,
            release_type=args.release_type,
            message=args.message,
            preview=getattr(args, "preview", False),
        )
    finally:
        os.chdir(original_dir)
