#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Lightweight helper functions around Git commands.

These helpers are intentionally small wrappers so that higher-level
logic (release, version, changelog) does not have to deal with the
details of subprocess handling.
"""

from __future__ import annotations

import subprocess
from typing import List, Optional


class GitError(RuntimeError):
    """Raised when a Git command fails in an unexpected way."""


def run_git(args: List[str], cwd: str = ".") -> str:
    """
    Run a Git command and return its stdout as a stripped string.

    Raises GitError if the command fails.
    """
    cmd = ["git"] + args
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise GitError(
            f"Git command failed in {cwd!r}: {' '.join(cmd)}\n"
            f"Exit code: {exc.returncode}\n"
            f"STDOUT:\n{exc.stdout}\n"
            f"STDERR:\n{exc.stderr}"
        ) from exc

    return result.stdout.strip()


def get_tags(cwd: str = ".") -> List[str]:
    """
    Return a list of all tags in the repository in `cwd`.

    If there are no tags, an empty list is returned.
    """
    try:
        output = run_git(["tag"], cwd=cwd)
    except GitError as exc:
        # If the repo has no tags or is not a git repo, surface a clear error.
        # You can decide later if you want to treat this differently.
        if "not a git repository" in str(exc):
            raise
        # No tags: stdout may just be empty; treat this as empty list.
        return []

    if not output:
        return []

    return [line.strip() for line in output.splitlines() if line.strip()]


def get_head_commit(cwd: str = ".") -> Optional[str]:
    """
    Return the current HEAD commit hash, or None if it cannot be determined.
    """
    try:
        output = run_git(["rev-parse", "HEAD"], cwd=cwd)
    except GitError:
        return None
    return output or None


def get_current_branch(cwd: str = ".") -> Optional[str]:
    """
    Return the current branch name, or None if it cannot be determined.

    Note: In detached HEAD state this will return 'HEAD'.
    """
    try:
        output = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    except GitError:
        return None
    return output or None
