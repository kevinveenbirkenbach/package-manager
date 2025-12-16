from __future__ import annotations

import os
import sys
from typing import List, Dict, Any

from pkgmgr.core.git.commands import pull_args, GitPullArgsError
from pkgmgr.core.repository.dir import get_repo_dir
from pkgmgr.core.repository.identifier import get_repo_identifier
from pkgmgr.core.repository.verify import verify_repository

Repository = Dict[str, Any]


def pull_with_verification(
    selected_repos: List[Repository],
    repositories_base_dir: str,
    all_repos: List[Repository],
    extra_args: List[str],
    no_verification: bool,
    preview: bool,
) -> None:
    """
    Execute `git pull` for each repository with verification.

    - If verification fails and verification is enabled, prompt user to continue.
    - Uses core.git.commands.pull_args() (no raw subprocess usage).
    """
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = get_repo_dir(repositories_base_dir, repo)

        if not os.path.exists(repo_dir):
            print(f"Repository directory '{repo_dir}' not found for {repo_identifier}.")
            continue

        verified_info = repo.get("verified")
        verified_ok, errors, _commit_hash, _signing_key = verify_repository(
            repo,
            repo_dir,
            mode="pull",
            no_verification=no_verification,
        )

        if not preview and not no_verification and verified_info and not verified_ok:
            print(f"Warning: Verification failed for {repo_identifier}:")
            for err in errors:
                print(f"  - {err}")
            choice = input("Proceed with 'git pull'? (y/N): ").strip().lower()
            if choice != "y":
                continue

        try:
            pull_args(extra_args, cwd=repo_dir, preview=preview)
        except GitPullArgsError as exc:
            # Keep behavior consistent with previous implementation:
            # stop on first failure and propagate return code as generic failure.
            print(str(exc))
            sys.exit(1)
