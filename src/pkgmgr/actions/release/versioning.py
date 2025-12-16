#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Version discovery and bumping helpers for the release workflow.
"""

from __future__ import annotations

from pkgmgr.core.git.queries import get_tags
from pkgmgr.core.version.semver import (
    SemVer,
    find_latest_version,
    bump_major,
    bump_minor,
    bump_patch,
)


def determine_current_version() -> SemVer:
    """
    Determine the current semantic version from Git tags.

    Behaviour:
      - If there are no tags or no SemVer-compatible tags, return 0.0.0.
      - Otherwise, use the latest SemVer tag as current version.
    """
    tags = get_tags()
    if not tags:
        return SemVer(0, 0, 0)

    latest = find_latest_version(tags)
    if latest is None:
        return SemVer(0, 0, 0)

    _tag, ver = latest
    return ver


def bump_semver(current: SemVer, release_type: str) -> SemVer:
    """
    Bump the given SemVer according to the release type.

    release_type must be one of: "major", "minor", "patch".
    """
    if release_type == "major":
        return bump_major(current)
    if release_type == "minor":
        return bump_minor(current)
    if release_type == "patch":
        return bump_patch(current)

    raise ValueError(f"Unknown release type: {release_type!r}")
