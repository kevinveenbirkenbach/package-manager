from __future__ import annotations

from typing import Optional

from pkgmgr.core.git.commands import (
    checkout,
    create_branch,
    fetch,
    pull,
    push_upstream,
)
from pkgmgr.core.git.queries import resolve_base_branch


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

    resolved_base = resolve_base_branch(base_branch, fallback_base, cwd=cwd)

    # Workflow (commands raise specific GitBaseError subclasses)
    fetch("origin", cwd=cwd)
    checkout(resolved_base, cwd=cwd)
    pull("origin", resolved_base, cwd=cwd)

    # Create new branch from resolved base and push it with upstream tracking
    create_branch(name, resolved_base, cwd=cwd)
    push_upstream("origin", name, cwd=cwd)
