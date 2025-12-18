#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utilities for working with semantic versions (SemVer).

This module is intentionally small and self-contained so it can be
used by release/version/changelog commands without pulling in any
heavy dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple


@dataclass(frozen=True, order=True)
class SemVer:
    """Simple semantic version representation (MAJOR.MINOR.PATCH)."""

    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> "SemVer":
        """
        Parse a version string like '1.2.3' or 'v1.2.3' into a SemVer.

        Raises ValueError if the format is invalid.
        """
        text = value.strip()
        if text.startswith("v"):
            text = text[1:]

        parts = text.split(".")
        if len(parts) != 3:
            raise ValueError(f"Not a valid semantic version: {value!r}")

        try:
            major = int(parts[0])
            minor = int(parts[1])
            patch = int(parts[2])
        except ValueError as exc:
            raise ValueError(
                f"Semantic version components must be integers: {value!r}"
            ) from exc

        if major < 0 or minor < 0 or patch < 0:
            raise ValueError(
                f"Semantic version components must be non-negative: {value!r}"
            )

        return cls(major=major, minor=minor, patch=patch)

    def to_tag(self, with_prefix: bool = True) -> str:
        """
        Convert the version into a tag string: 'v1.2.3' (default) or '1.2.3'.
        """
        core = f"{self.major}.{self.minor}.{self.patch}"
        return f"v{core}" if with_prefix else core

    def __str__(self) -> str:
        return self.to_tag(with_prefix=False)


def is_semver_tag(tag: str) -> bool:
    """
    Return True if the given tag string looks like a SemVer tag.

    Accepts both '1.2.3' and 'v1.2.3' formats.
    """
    try:
        SemVer.parse(tag)
        return True
    except ValueError:
        return False


def extract_semver_from_tags(
    tags: Iterable[str],
    major: Optional[int] = None,
    minor: Optional[int] = None,
) -> List[Tuple[str, SemVer]]:
    """
    Filter and parse tags that match SemVer, optionally restricted
    to a specific MAJOR or MAJOR.MINOR line.

    Returns a list of (tag_string, SemVer) pairs.
    """
    result: List[Tuple[str, SemVer]] = []
    for tag in tags:
        try:
            ver = SemVer.parse(tag)
        except ValueError:
            # Ignore non-SemVer tags
            continue

        if major is not None and ver.major != major:
            continue
        if minor is not None and ver.minor != minor:
            continue

        result.append((tag, ver))

    return result


def find_latest_version(
    tags: Iterable[str],
    major: Optional[int] = None,
    minor: Optional[int] = None,
) -> Optional[Tuple[str, SemVer]]:
    """
    Find the latest SemVer tag from the given tags.

    If `major` is given, only consider that MAJOR line.
    If `minor` is given as well, only consider that MAJOR.MINOR line.

    Returns a tuple (tag_string, SemVer) or None if no SemVer tag matches.
    """
    candidates = extract_semver_from_tags(tags, major=major, minor=minor)
    if not candidates:
        return None

    # SemVer is orderable thanks to dataclass(order=True)
    tag, ver = max(candidates, key=lambda item: item[1])
    return tag, ver


def bump_major(version: SemVer) -> SemVer:
    """
    Bump MAJOR: MAJOR+1.0.0
    """
    return SemVer(major=version.major + 1, minor=0, patch=0)


def bump_minor(version: SemVer) -> SemVer:
    """
    Bump MINOR: MAJOR.MINOR+1.0
    """
    return SemVer(major=version.major, minor=version.minor + 1, patch=0)


def bump_patch(version: SemVer) -> SemVer:
    """
    Bump PATCH: MAJOR.MINOR.PATCH+1
    """
    return SemVer(major=version.major, minor=version.minor, patch=version.patch + 1)
