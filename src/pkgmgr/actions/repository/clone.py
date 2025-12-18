from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from pkgmgr.core.git.commands import clone as git_clone, GitCloneError
from pkgmgr.core.repository.dir import get_repo_dir
from pkgmgr.core.repository.identifier import get_repo_identifier
from pkgmgr.core.repository.verify import verify_repository

Repository = Dict[str, Any]


def _build_clone_url(repo: Repository, clone_mode: str) -> Optional[str]:
    provider = repo.get("provider")
    account = repo.get("account")
    name = repo.get("repository")
    replacement = repo.get("replacement")

    if clone_mode == "ssh":
        if not provider or not account or not name:
            return None
        return f"git@{provider}:{account}/{name}.git"

    if clone_mode in ("https", "shallow"):
        if replacement:
            return f"https://{replacement}.git"
        if not provider or not account or not name:
            return None
        return f"https://{provider}/{account}/{name}.git"

    return None


def clone_repos(
    selected_repos: List[Repository],
    repositories_base_dir: str,
    all_repos: List[Repository],
    preview: bool,
    no_verification: bool,
    clone_mode: str,
) -> None:
    for repo in selected_repos:
        repo_identifier = get_repo_identifier(repo, all_repos)
        repo_dir = get_repo_dir(repositories_base_dir, repo)

        if os.path.exists(repo_dir):
            print(
                f"[INFO] Repository '{repo_identifier}' already exists at '{repo_dir}'. Skipping clone."
            )
            continue

        parent_dir = os.path.dirname(repo_dir)
        os.makedirs(parent_dir, exist_ok=True)

        clone_url = _build_clone_url(repo, clone_mode)
        if not clone_url:
            print(
                f"[WARNING] Cannot build clone URL for '{repo_identifier}'. Skipping."
            )
            continue

        shallow = clone_mode == "shallow"
        mode_label = "HTTPS (shallow)" if shallow else clone_mode.upper()

        print(
            f"[INFO] Attempting to clone '{repo_identifier}' using {mode_label} "
            f"from {clone_url} into '{repo_dir}'."
        )

        try:
            args = []
            if shallow:
                args += ["--depth", "1", "--single-branch"]
            args += [clone_url, repo_dir]

            git_clone(
                args,
                cwd=parent_dir,
                preview=preview,
            )

        except GitCloneError as exc:
            if clone_mode != "ssh":
                print(f"[WARNING] Clone failed for '{repo_identifier}': {exc}")
                continue

            print(f"[WARNING] SSH clone failed for '{repo_identifier}': {exc}")
            choice = (
                input("Do you want to attempt HTTPS clone instead? (y/N): ")
                .strip()
                .lower()
            )
            if choice != "y":
                print(f"[INFO] HTTPS clone not attempted for '{repo_identifier}'.")
                continue

            fallback_url = _build_clone_url(repo, "https")
            if not fallback_url:
                print(f"[WARNING] Cannot build HTTPS URL for '{repo_identifier}'.")
                continue

            print(
                f"[INFO] Attempting to clone '{repo_identifier}' using HTTPS "
                f"from {fallback_url} into '{repo_dir}'."
            )

            try:
                git_clone(
                    [fallback_url, repo_dir],
                    cwd=parent_dir,
                    preview=preview,
                )
            except GitCloneError as exc2:
                print(f"[WARNING] HTTPS clone failed for '{repo_identifier}': {exc2}")
                continue

        verified_info = repo.get("verified")
        if not verified_info:
            continue

        verified_ok, errors, _commit_hash, _signing_key = verify_repository(
            repo,
            repo_dir,
            mode="local",
            no_verification=no_verification,
        )

        if no_verification or verified_ok:
            continue

        print(f"Warning: Verification failed for {repo_identifier} after cloning:")
        for err in errors:
            print(f"  - {err}")

        choice = input("Proceed anyway? (y/N): ").strip().lower()
        if choice != "y":
            print(f"Skipping repository {repo_identifier} due to failed verification.")
