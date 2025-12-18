from __future__ import annotations

from typing import Optional

from pkgmgr.core.git.errors import GitRunError
from pkgmgr.core.git.queries import get_current_branch
from pkgmgr.core.git.commands import (
    GitDeleteRemoteBranchError,
    delete_local_branch,
    delete_remote_branch,
)

from pkgmgr.core.git.queries import resolve_base_branch


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
        except GitRunError as exc:
            raise RuntimeError(f"Failed to detect current branch: {exc}") from exc

    if not name:
        raise RuntimeError("Branch name must not be empty.")

    target_base = resolve_base_branch(base_branch, fallback_base, cwd=cwd)

    if name == target_base:
        raise RuntimeError(
            f"Refusing to drop base branch {target_base!r}. It cannot be deleted."
        )

    # Confirmation
    if not force:
        answer = (
            input(
                f"Delete branch '{name}' locally and on origin? This is destructive! (y/N): "
            )
            .strip()
            .lower()
        )
        if answer != "y":
            print("Aborted dropping branch.")
            return

    delete_local_branch(name, cwd=cwd, force=False)

    # Remote delete (special-case message)
    try:
        delete_remote_branch("origin", name, cwd=cwd)
    except GitDeleteRemoteBranchError as exc:
        raise RuntimeError(
            f"Branch {name!r} was deleted locally, but remote deletion failed: {exc}"
        ) from exc
