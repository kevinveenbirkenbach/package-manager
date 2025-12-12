from __future__ import annotations
from typing import Optional
from pkgmgr.core.git import run_git, GitError, get_current_branch
from .utils import _resolve_base_branch


def drop_branch(
    name: Optional[str],
    base_branch: str = "main",
    fallback_base: str = "master",
    cwd: str = ".",
    force: bool = False,
) -> None:
    """
    Delete a branch locally and remotely without merging.
    """

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
            f"Refusing to drop base branch {target_base!r}. It cannot be deleted."
        )

    # Confirmation
    if not force:
        answer = input(
            f"Delete branch '{name}' locally and on origin? This is destructive! (y/N): "
        ).strip().lower()
        if answer != "y":
            print("Aborted dropping branch.")
            return

    # Local delete
    try:
        run_git(["branch", "-d", name], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(f"Failed to delete local branch {name!r}: {exc}") from exc

    # Remote delete
    try:
        run_git(["push", "origin", "--delete", name], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Branch {name!r} was deleted locally, but remote deletion failed: {exc}"
        ) from exc
