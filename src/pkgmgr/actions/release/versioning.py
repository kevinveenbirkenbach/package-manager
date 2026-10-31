"""
Version discovery and bumping helpers for the release workflow.
"""

from __future__ import annotations

import re

from pkgmgr.core.git.queries import get_tags
from pkgmgr.core.version.semver import (
    SemVer,
    bump_major,
    bump_minor,
    bump_patch,
    find_latest_version,
)
from pkgmgr.core.version.source import (
    read_cargo_version,
    read_changelog_version,
    read_debian_changelog_version,
    read_flake_version,
    read_pkgbuild_version,
    read_pyproject_version,
    read_spec_version,
)

FILE_SOURCES = {
    "pyproject.toml": read_pyproject_version,
    "CHANGELOG.md": read_changelog_version,
    "flake.nix": read_flake_version,
    "PKGBUILD": read_pkgbuild_version,
    "RPM spec": read_spec_version,
    "debian/changelog": read_debian_changelog_version,
    "Cargo.toml": read_cargo_version,
}
_CORE_VERSION = re.compile(r"^v?(\d+\.\d+\.\d+)")


def _file_versions(repo_dir: str) -> dict[str, SemVer]:
    versions: dict[str, SemVer] = {}
    for source, read in FILE_SOURCES.items():
        match = _CORE_VERSION.match(read(repo_dir) or "")
        if match:
            versions[source] = SemVer.parse(match.group(1))
    return versions


def determine_current_version(repo_dir: str) -> SemVer:
    """
    Determine the highest version across the latest SemVer tag and every
    version file the release writes.

    Args:
        repo_dir: repository root holding the version files.

    Returns:
        The highest version found, or 0.0.0 when no source has one.
    """
    versions = _file_versions(repo_dir)
    latest = find_latest_version(get_tags() or [])
    if latest is not None:
        versions["tag"] = latest[1]
    if not versions:
        return SemVer(0, 0, 0)

    highest = max(versions.values())
    if len(set(versions.values())) > 1:
        found = ", ".join(f"{source} {ver}" for source, ver in versions.items())
        print(f"[INFO] Version sources disagree ({found}); starting from {highest}.")
    return highest


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
