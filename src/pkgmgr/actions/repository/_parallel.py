from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Tuple

from pkgmgr.core.repository.dir import get_repo_dir
from pkgmgr.core.repository.identifier import get_repo_identifier

Repository = Dict[str, Any]
RepoRef = Tuple[str, str]
OpResult = Tuple[bool, str]
RepoOp = Callable[[str], OpResult]


def resolve_repos(
    selected_repos: List[Repository],
    repositories_base_dir: str,
    all_repos: List[Repository],
) -> List[RepoRef]:
    """
    Resolve ``(identifier, repo_dir)`` pairs for ``selected_repos``.

    Repositories whose directory does not exist on disk are reported and
    skipped, matching the prior behavior of pull/push handlers.
    """
    resolved: List[RepoRef] = []
    for repo in selected_repos:
        ident = get_repo_identifier(repo, all_repos)
        rd = get_repo_dir(repositories_base_dir, repo)
        if not os.path.exists(rd):
            print(f"Repository directory '{rd}' not found for {ident}.")
            continue
        resolved.append((ident, rd))
    return resolved


def run_on_repos(
    repos: List[RepoRef],
    op: RepoOp,
    *,
    jobs: int,
    op_name: str,
) -> None:
    """
    Run ``op(repo_dir) -> (ok, msg)`` for each repo, optionally in parallel.

    - ``jobs == 1``: serial, quiet on success, prints ``msg`` on failure.
    - ``jobs  > 1``: parallel via ThreadPoolExecutor, prints a banner plus
      ``[OK]``/``[FAIL]`` per repo and a final summary.
    - Exits with status 1 if any operation failed.
    """
    if not repos:
        return

    effective_jobs = max(1, min(jobs, len(repos)))
    failed: List[Tuple[str, str]] = []

    if effective_jobs == 1:
        for ident, rd in repos:
            ok, msg = op(rd)
            if not ok:
                print(msg)
                failed.append((ident, msg))
    else:
        print(
            f"[{op_name.upper()}] Running {len(repos)} {op_name}(s) with up to "
            f"{effective_jobs} parallel jobs..."
        )
        with ThreadPoolExecutor(max_workers=effective_jobs) as executor:
            futures = {executor.submit(op, rd): ident for ident, rd in repos}
            for future in as_completed(futures):
                ident = futures[future]
                ok, msg = future.result()
                if ok:
                    print(f"[OK]   {ident}")
                else:
                    print(f"[FAIL] {ident}")
                    for line in msg.splitlines():
                        print(f"       {line}")
                    failed.append((ident, msg))

    if failed:
        if effective_jobs > 1:
            print(
                f"\n[SUMMARY] {len(failed)} of {len(repos)} {op_name}(s) failed:"
            )
            for ident, _msg in failed:
                print(f"  - {ident}")
        sys.exit(1)
