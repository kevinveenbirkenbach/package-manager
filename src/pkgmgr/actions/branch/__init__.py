# pkgmgr/actions/branch/__init__.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
High-level helpers for branch-related operations.

This module encapsulates the actual Git logic so the CLI layer
(pkgmgr.cli.commands.branch) stays thin and testable.
"""

from __future__ import annotations

from typing import Optional

from pkgmgr.core.git import run_git, GitError, get_current_branch


# ---------------------------------------------------------------------------
# Branch creation (open)
# ---------------------------------------------------------------------------

def open_branch(
    name: Optional[str],
    base_branch: str = "main",
    fallback_base: str = "master",
    cwd: str = ".",
) -> None:
    """
    Create and push a new feature branch on top of a base branch.

    The base branch is resolved by:
        1. Trying 'base_branch' (default: 'main')
        2. Falling back to 'fallback_base' (default: 'master')

    Steps:
        1) git fetch origin
        2) git checkout <resolved_base>
        3) git pull origin <resolved_base>
        4) git checkout -b <name>
        5) git push -u origin <name>

    If `name` is None or empty, the user is prompted to enter one.
    """

    # Request name interactively if not provided
    if not name:
        name = input("Enter new branch name: ").strip()

    if not name:
        raise RuntimeError("Branch name must not be empty.")

    # Resolve which base branch to use (main or master)
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

    # 3) Pull latest changes for base branch
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

    # 5) Push new branch to origin
    try:
        run_git(["push", "-u", "origin", name], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to push new branch {name!r} to origin: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Base branch resolver (shared by open/close)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Branch closing (merge + deletion)
# ---------------------------------------------------------------------------

def close_branch(
    name: Optional[str],
    base_branch: str = "main",
    fallback_base: str = "master",
    cwd: str = ".",
) -> None:
    """
    Merge a feature branch into the base branch and delete it afterwards.

    Steps:
        1) Determine the branch name (argument or current branch)
        2) Resolve base branch (main/master)
        3) Ask for confirmation
        4) git fetch origin
        5) git checkout <base>
        6) git pull origin <base>
        7) git merge --no-ff <name>
        8) git push origin <base>
        9) Delete branch locally
       10) Delete branch on origin (best effort)
    """

    # 1) Determine which branch should be closed
    if not name:
        try:
            name = get_current_branch(cwd=cwd)
        except GitError as exc:
            raise RuntimeError(f"Failed to detect current branch: {exc}") from exc

    if not name:
        raise RuntimeError("Branch name must not be empty.")

    # 2) Resolve base branch
    target_base = _resolve_base_branch(base_branch, fallback_base, cwd=cwd)

    if name == target_base:
        raise RuntimeError(
            f"Refusing to close base branch {target_base!r}. "
            "Please specify a feature branch."
        )

    # 3) Ask user for confirmation
    prompt = (
        f"Merge branch '{name}' into '{target_base}' and delete it afterwards? "
        "(y/N): "
    )
    answer = input(prompt).strip().lower()
    if answer != "y":
        print("Aborted closing branch.")
        return

    # 4) Fetch from origin
    try:
        run_git(["fetch", "origin"], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to fetch from origin before closing branch {name!r}: {exc}"
        ) from exc

    # 5) Checkout base
    try:
        run_git(["checkout", target_base], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to checkout base branch {target_base!r}: {exc}"
        ) from exc

    # 6) Pull latest base state
    try:
        run_git(["pull", "origin", target_base], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to pull latest changes for base branch {target_base!r}: {exc}"
        ) from exc

    # 7) Merge the feature branch
    try:
        run_git(["merge", "--no-ff", name], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to merge branch {name!r} into {target_base!r}: {exc}"
        ) from exc

    # 8) Push updated base
    try:
        run_git(["push", "origin", target_base], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to push base branch {target_base!r} after merge: {exc}"
        ) from exc

    # 9) Delete branch locally
    try:
        run_git(["branch", "-d", name], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to delete local branch {name!r}: {exc}"
        ) from exc

    # 10) Delete branch on origin (best effort)
    try:
        run_git(["push", "origin", "--delete", name], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Branch {name!r} was deleted locally, but remote deletion failed: {exc}"
        ) from exc
