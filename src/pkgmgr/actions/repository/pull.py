from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Tuple

from pkgmgr.actions.repository._parallel import RepoRef, run_on_repos
from pkgmgr.core.git.commands import pull_args, GitPullArgsError
from pkgmgr.core.repository.identifier import get_repo_identifier
from pkgmgr.core.repository.dir import get_repo_dir
from pkgmgr.core.repository.verify import verify_repository

Repository = Dict[str, Any]


def _pull_one(repo_dir: str, extra_args: List[str], preview: bool) -> Tuple[bool, str]:
    try:
        pull_args(extra_args, cwd=repo_dir, preview=preview)
        return (True, "")
    except GitPullArgsError as exc:
        return (False, str(exc))


def _verify_one(
    repo: Repository,
    repo_dir: str,
    no_verification: bool,
) -> Tuple[bool, bool, List[str]]:
    """Returns (has_verified_info, verified_ok, errors)."""
    verified_ok, errors, _commit, _key = verify_repository(
        repo, repo_dir, mode="pull", no_verification=no_verification,
    )
    return (bool(repo.get("verified")), verified_ok, errors)


def _verify_all(
    candidates: List[Tuple[Repository, str, str]],
    no_verification: bool,
    jobs: int,
) -> List[Tuple[str, str, bool, bool, List[str]]]:
    """
    Verify all candidates (parallel if ``jobs > 1``), preserving input order.

    Returns one tuple per candidate: ``(ident, repo_dir, has_verified_info,
    verified_ok, errors)``.
    """
    verify_jobs = max(1, min(jobs, len(candidates)))
    if verify_jobs == 1:
        return [
            (ident, rd, *_verify_one(repo, rd, no_verification))
            for repo, ident, rd in candidates
        ]
    with ThreadPoolExecutor(max_workers=verify_jobs) as executor:
        futures = [
            executor.submit(_verify_one, repo, rd, no_verification)
            for repo, _ident, rd in candidates
        ]
        results = [f.result() for f in futures]
    return [
        (ident, rd, *res) for (_repo, ident, rd), res in zip(candidates, results)
    ]


def pull_with_verification(
    selected_repos: List[Repository],
    repositories_base_dir: str,
    all_repos: List[Repository],
    extra_args: List[str],
    no_verification: bool,
    preview: bool,
    jobs: int = 1,
) -> None:
    """
    Execute `git pull` for each repository with verification.

    - Verification (I/O-bound) runs in parallel when ``jobs > 1``.
    - Interactive prompts for failed verifications are handled serially on the
      main thread after parallel verification completes.
    - Approved repos are then pulled in parallel when ``jobs > 1``.
    - On any pull failure, prints a summary and exits with status 1.
    """
    candidates: List[Tuple[Repository, str, str]] = []
    for repo in selected_repos:
        ident = get_repo_identifier(repo, all_repos)
        rd = get_repo_dir(repositories_base_dir, repo)
        if not os.path.exists(rd):
            print(f"Repository directory '{rd}' not found for {ident}.")
            continue
        candidates.append((repo, ident, rd))

    if not candidates:
        return

    verify_results = _verify_all(candidates, no_verification, jobs)

    approved: List[RepoRef] = []
    for ident, rd, has_verified_info, verified_ok, errors in verify_results:
        if not preview and not no_verification and has_verified_info and not verified_ok:
            print(f"Warning: Verification failed for {ident}:")
            for err in errors:
                print(f"  - {err}")
            choice = input("Proceed with 'git pull'? (y/N): ").strip().lower()
            if choice != "y":
                continue
        approved.append((ident, rd))

    run_on_repos(
        approved,
        lambda rd: _pull_one(rd, extra_args, preview),
        jobs=jobs,
        op_name="pull",
    )
