#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
High-level helpers for branch-related operations.

This module encapsulates the actual Git logic so the CLI layer
(pkgmgr.cli_core.commands.branch) stays thin and testable.
"""

from __future__ import annotations

from typing import Optional

from pkgmgr.git_utils import run_git, GitError


def open_branch(
    name: Optional[str],
    base_branch: str = "main",
    cwd: str = ".",
) -> None:
    """
    Create and push a new feature branch on top of `base_branch`.

    Steps:
      1) git fetch origin
      2) git checkout <base_branch>
      3) git pull origin <base_branch>
      4) git checkout -b <name>
      5) git push -u origin <name>

    If `name` is None or empty, the user is prompted on stdin.
    """

    if not name:
        name = input("Enter new branch name: ").strip()

    if not name:
        raise RuntimeError("Branch name must not be empty.")

    # 1) Fetch from origin
    try:
        run_git(["fetch", "origin"], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to fetch from origin before creating branch {name!r}: {exc}"
        ) from exc

    # 2) Checkout base branch
    try:
        run_git(["checkout", base_branch], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to checkout base branch {base_branch!r}: {exc}"
        ) from exc

    # 3) Pull latest changes on base
    try:
        run_git(["pull", "origin", base_branch], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to pull latest changes for base branch {base_branch!r}: {exc}"
        ) from exc

    # 4) Create new branch
    try:
        run_git(["checkout", "-b", name], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to create new branch {name!r} from base {base_branch!r}: {exc}"
        ) from exc

    # 5) Push and set upstream
    try:
        run_git(["push", "-u", "origin", name], cwd=cwd)
    except GitError as exc:
        raise RuntimeError(
            f"Failed to push new branch {name!r} to origin: {exc}"
        ) from exc
