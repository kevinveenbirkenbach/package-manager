#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Helpers to generate changelog information from Git history.
"""

from __future__ import annotations

from typing import Optional

from pkgmgr.core.git.queries import (
    get_changelog,
    GitChangelogQueryError,
)


def generate_changelog(
    cwd: str,
    from_ref: Optional[str] = None,
    to_ref: Optional[str] = None,
    include_merges: bool = False,
) -> str:
    """
    Generate a plain-text changelog between two Git refs.

    Returns a human-readable message instead of raising.
    """
    if to_ref is None:
        to_ref = "HEAD"

    rev_range = f"{from_ref}..{to_ref}" if from_ref else to_ref
    try:
        output = get_changelog(
            cwd=cwd,
            from_ref=from_ref,
            to_ref=to_ref,
            include_merges=include_merges,
        )
    except GitChangelogQueryError as exc:
        return (
            f"[ERROR] Failed to generate changelog in {cwd!r} "
            f"for range {rev_range!r}:\n{exc}"
        )

    if not output.strip():
        return f"[INFO] No commits found for range {rev_range!r}."

    return output.strip()
