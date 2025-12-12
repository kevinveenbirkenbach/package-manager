from __future__ import annotations
from typing import Optional
from pkgmgr.core.git import run_git, GitError, get_current_branch
from .utils import _resolve_base_branch


def close_branch(
    name: Optional[str],
    base_branch: str = "main",
    fallback_base: str = "master",
    cwd: str = ".",
    force: bool = False,
) -> None:
    """
    Merge a feature branch into the base branch and delete it afterwards.
    """

    # Determine branch name
    if not name:
        try:
            name = get_current_branch(cwd=cwd)
        except GitError as exc:
            raise RuntimeError(f"Failed to detect current branch: {exc}") from exc

    if not name:
        raise RuntimeError("Branch name must not be empty.")

    target_base = _resolve_base_branch(base_branch, fallback_base, cwd=cwd)

    if name == target_base:
        raise RuntimeError(
            f"Refusing to close base branch {target_base!r}. "
            "Please specify a feature branch."
        )

    # Confirmation
    if not force:
        answer = input(
            f"Merge branch '{name}' into '{target_base}' and delete it afterwards? (y/N): "
        ).strip().lower()
        if answer != "y":
            print("Aborted closing branch.")
            return

    # Fetch
    try:
        run_git(["fetch", "origin"], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to fetch from origin before closing branch {name!r}: {exc}"
        ) from exc

    # Checkout base
    try:
        run_git(["checkout", target_base], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to checkout base branch {target_base!r}: {exc}"
        ) from exc

    # Pull latest
    try:
        run_git(["pull", "origin", target_base], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to pull latest changes for base branch {target_base!r}: {exc}"
        ) from exc

    # Merge
    try:
        run_git(["merge", "--no-ff", name], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to merge branch {name!r} into {target_base!r}: {exc}"
        ) from exc

    # Push result
    try:
        run_git(["push", "origin", target_base], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to push base branch {target_base!r} after merge: {exc}"
        ) from exc

    # Delete local
    try:
        run_git(["branch", "-d", name], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to delete local branch {name!r}: {exc}"
        ) from exc

    # Delete remote
    try:
        run_git(["push", "origin", "--delete", name], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Branch {name!r} deleted locally, but remote deletion failed: {exc}"
        ) from exc
