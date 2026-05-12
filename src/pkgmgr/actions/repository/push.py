from __future__ import annotations

from typing import Any, Dict, List, Tuple

from pkgmgr.actions.repository._parallel import (
    resolve_repos,
    run_on_repos,
)
from pkgmgr.core.git.commands import push_args, GitPushArgsError

Repository = Dict[str, Any]


def _push_one(repo_dir: str, extra_args: List[str], preview: bool) -> Tuple[bool, str]:
    try:
        push_args(extra_args, cwd=repo_dir, preview=preview)
        return (True, "")
    except GitPushArgsError as exc:
        return (False, str(exc))


def push_in_parallel(
    selected_repos: List[Repository],
    repositories_base_dir: str,
    all_repos: List[Repository],
    extra_args: List[str],
    preview: bool,
    jobs: int = 1,
) -> None:
    """
    Execute `git push` for each repository, optionally in parallel.
    """
    repos = resolve_repos(selected_repos, repositories_base_dir, all_repos)
    run_on_repos(
        repos,
        lambda rd: _push_one(rd, extra_args, preview),
        jobs=jobs,
        op_name="push",
    )
