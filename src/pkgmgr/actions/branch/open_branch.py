from __future__ import annotations
from typing import Optional
from pkgmgr.core.git import run_git, GitError
from .utils import _resolve_base_branch


def open_branch(
    name: Optional[str],
    base_branch: str = "main",
    fallback_base: str = "master",
    cwd: str = ".",
) -> None:
    """
    Create and push a new feature branch on top of a base branch.
    """

    # Request name interactively if not provided
    if not name:
        name = input("Enter new branch name: ").strip()

    if not name:
        raise RuntimeError("Branch name must not be empty.")

    resolved_base = _resolve_base_branch(base_branch, fallback_base, cwd=cwd)

    # 1) Fetch from origin
    try:
        run_git(["fetch", "origin"], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to fetch from origin before creating branch {name!r}: {exc}"
        ) from exc

    # 2) Checkout base branch
    try:
        run_git(["checkout", resolved_base], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to checkout base branch {resolved_base!r}: {exc}"
        ) from exc

    # 3) Pull latest changes
    try:
        run_git(["pull", "origin", resolved_base], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to pull latest changes for base branch {resolved_base!r}: {exc}"
        ) from exc

    # 4) Create new branch
    try:
        run_git(["checkout", "-b", name], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to create new branch {name!r} from base {resolved_base!r}: {exc}"
        ) from exc

    # 5) Push new branch
    try:
        run_git(["push", "-u", "origin", name], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to push new branch {name!r} to origin: {exc}"
        ) from exc
