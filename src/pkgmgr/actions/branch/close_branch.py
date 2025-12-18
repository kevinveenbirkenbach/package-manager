from __future__ import annotations

from typing import Optional

from pkgmgr.core.git.errors import GitRunError
from pkgmgr.core.git.queries import get_current_branch
from pkgmgr.core.git.commands import (
    GitDeleteRemoteBranchError,
    checkout,
    delete_local_branch,
    delete_remote_branch,
    fetch,
    merge_no_ff,
    pull,
    push,
)

from pkgmgr.core.git.queries import resolve_base_branch


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
        except GitRunError as exc:
            raise RuntimeError(f"Failed to detect current branch: {exc}") from exc

    if not name:
        raise RuntimeError("Branch name must not be empty.")

    target_base = resolve_base_branch(base_branch, fallback_base, cwd=cwd)

    if name == target_base:
        raise RuntimeError(
            f"Refusing to close base branch {target_base!r}. "
            "Please specify a feature branch."
        )

    # Confirmation
    if not force:
        answer = (
            input(
                f"Merge branch '{name}' into '{target_base}' and delete it afterwards? (y/N): "
            )
            .strip()
            .lower()
        )
        if answer != "y":
            print("Aborted closing branch.")
            return

    # Execute workflow (commands raise specific GitRunError subclasses)
    fetch("origin", cwd=cwd)
    checkout(target_base, cwd=cwd)
    pull("origin", target_base, cwd=cwd)
    merge_no_ff(name, cwd=cwd)
    push("origin", target_base, cwd=cwd)

    # Delete local branch (safe delete by default)
    delete_local_branch(name, cwd=cwd, force=False)

    # Delete remote branch (special-case error message)
    try:
        delete_remote_branch("origin", name, cwd=cwd)
    except GitDeleteRemoteBranchError as exc:
        raise RuntimeError(
            f"Branch {name!r} deleted locally, but remote deletion failed: {exc}"
        ) from exc
