#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Helpers to generate changelog information from Git history.

This module provides a small abstraction around `git log` so that
CLI commands can request a changelog between two refs (tags, branches,
commits) without dealing with raw subprocess calls.
"""

from __future__ import annotations

from typing import Optional

from pkgmgr.core.git import run_git, GitError


def generate_changelog(
    cwd: str,
    from_ref: Optional[str] = None,
    to_ref: Optional[str] = None,
    include_merges: bool = False,
) -> str:
    """
    Generate a plain-text changelog between two Git refs.

    Parameters
    ----------
    cwd:
        Repository directory in which to run Git commands.
    from_ref:
        Optional starting reference (exclusive). If provided together
        with `to_ref`, the range `from_ref..to_ref` is used.
        If only `from_ref` is given, the range `from_ref..HEAD` is used.
    to_ref:
        Optional end reference (inclusive). If omitted, `HEAD` is used.
    include_merges:
        If False (default), merge commits are filtered out.

    Returns
    -------
    str
        The output of `git log` formatted as a simple text changelog.
        If no commits are found or Git fails, an explanatory message
        is returned instead of raising.
    """
    # Determine the revision range
    if to_ref is None:
        to_ref = "HEAD"

    if from_ref:
        rev_range = f"{from_ref}..{to_ref}"
    else:
        rev_range = to_ref

    # Use a custom pretty format that includes tags/refs (%d)
    cmd = [
        "log",
        "--pretty=format:%h %d %s",
    ]
    if not include_merges:
        cmd.append("--no-merges")
    cmd.append(rev_range)

    try:
        output = run_git(cmd, cwd=cwd)
    except GitError as exc:
        # Do not raise to the CLI, return a human-readable error instead.
        return (
            f"[ERROR] Failed to generate changelog in {cwd!r} "
            f"for range {rev_range!r}:\n{exc}"
        )

    if not output.strip():
        return f"[INFO] No commits found for range {rev_range!r}."

    return output.strip()
