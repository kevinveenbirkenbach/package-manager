from __future__ import annotations
from pkgmgr.core.git import run_git, GitError


def _resolve_base_branch(
    preferred: str,
    fallback: str,
    cwd: str,
) -> str:
    """
    Resolve the base branch to use.

    Try `preferred` first (default: main),
    fall back to `fallback` (default: master).

    Raise RuntimeError if neither exists.
    """
    for candidate in (preferred, fallback):
        try:
            run_git(["rev-parse", "--verify", candidate], cwd=cwd)
            return candidate
        except GitError:
            continue

    raise RuntimeError(
        f"Neither {preferred!r} nor {fallback!r} exist in this repository."
    )
