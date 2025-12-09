#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Release helper for pkgmgr (public entry point).

This package provides the high-level `release()` function used by the
pkgmgr CLI to perform versioned releases:

  - Determine the next semantic version based on existing Git tags.
  - Update pyproject.toml with the new version.
  - Update additional packaging files (flake.nix, PKGBUILD,
    debian/changelog, RPM spec) where present.
  - Prepend a basic entry to CHANGELOG.md.
  - Move the floating 'latest' tag to the newly created release tag so
    the newest release is always marked as latest.

Additional behaviour:
  - If `preview=True` (from --preview), no files are written and no
    Git commands are executed. Instead, a detailed summary of the
    planned changes and commands is printed.
  - If `preview=False` and not forced, the release is executed in two
    phases:
      1) Preview-only run (dry-run).
      2) Interactive confirmation, then real release if confirmed.
    This confirmation can be skipped with the `force=True` flag.
  - Before creating and pushing tags, main/master is updated from origin
    when the release is performed on one of these branches.
  - If `close=True` is used and the current branch is not main/master,
    the branch will be closed via branch_commands.close_branch() after
    a successful release.
"""

from __future__ import annotations

import os
import sys
from typing import Optional

from pkgmgr.core.git import get_current_branch, GitError
from pkgmgr.actions.branch import close_branch

from .versioning import determine_current_version, bump_semver
from .git_ops import run_git_command, sync_branch_with_remote, update_latest_tag
from .files import (
    update_pyproject_version,
    update_flake_version,
    update_pkgbuild_version,
    update_spec_version,
    update_changelog,
    update_debian_changelog,
)


# ---------------------------------------------------------------------------
# Internal implementation (single-phase, preview or real)
# ---------------------------------------------------------------------------


def _release_impl(
    pyproject_path: str = "pyproject.toml",
    changelog_path: str = "CHANGELOG.md",
    release_type: str = "patch",
    message: Optional[str] = None,
    preview: bool = False,
    close: bool = False,
) -> None:
    """
    Internal implementation that performs a single-phase release.
    """
    current_ver = determine_current_version()
    new_ver = bump_semver(current_ver, release_type)
    new_ver_str = str(new_ver)
    new_tag = new_ver.to_tag(with_prefix=True)

    mode = "PREVIEW" if preview else "REAL"
    print(f"Release mode: {mode}")
    print(f"Current version: {current_ver}")
    print(f"New version:     {new_ver_str} ({release_type})")

    repo_root = os.path.dirname(os.path.abspath(pyproject_path))

    # Update core project metadata and packaging files
    update_pyproject_version(pyproject_path, new_ver_str, preview=preview)
    changelog_message = update_changelog(
        changelog_path,
        new_ver_str,
        message=message,
        preview=preview,
    )

    flake_path = os.path.join(repo_root, "flake.nix")
    update_flake_version(flake_path, new_ver_str, preview=preview)

    pkgbuild_path = os.path.join(repo_root, "PKGBUILD")
    update_pkgbuild_version(pkgbuild_path, new_ver_str, preview=preview)

    spec_path = os.path.join(repo_root, "package-manager.spec")
    update_spec_version(spec_path, new_ver_str, preview=preview)

    effective_message: Optional[str] = message
    if effective_message is None and isinstance(changelog_message, str):
        if changelog_message.strip():
            effective_message = changelog_message.strip()

    debian_changelog_path = os.path.join(repo_root, "debian", "changelog")
    package_name = os.path.basename(repo_root) or "package-manager"
    update_debian_changelog(
        debian_changelog_path,
        package_name=package_name,
        new_version=new_ver_str,
        message=effective_message,
        preview=preview,
    )

    commit_msg = f"Release version {new_ver_str}"
    tag_msg = effective_message or commit_msg

    # Determine branch and ensure it is up to date if main/master
    try:
        branch = get_current_branch() or "main"
    except GitError:
        branch = "main"
    print(f"Releasing on branch: {branch}")

    # Ensure main/master are up-to-date from origin before creating and
    # pushing tags. For other branches we only log the intent.
    sync_branch_with_remote(branch, preview=preview)

    files_to_add = [
        pyproject_path,
        changelog_path,
        flake_path,
        pkgbuild_path,
        spec_path,
        debian_changelog_path,
    ]
    existing_files = [p for p in files_to_add if p and os.path.exists(p)]

    if preview:
        for path in existing_files:
            print(f"[PREVIEW] Would run: git add {path}")
        print(f'[PREVIEW] Would run: git commit -am "{commit_msg}"')
        print(f'[PREVIEW] Would run: git tag -a {new_tag} -m "{tag_msg}"')
        print(f"[PREVIEW] Would run: git push origin {branch}")
        print("[PREVIEW] Would run: git push origin --tags")

        # Also update the floating 'latest' tag to the new highest SemVer.
        update_latest_tag(new_tag, preview=True)

        if close and branch not in ("main", "master"):
            print(
                f"[PREVIEW] Would also close branch {branch} after the release "
                "(close=True and branch is not main/master)."
            )
        elif close:
            print(
                f"[PREVIEW] close=True but current branch is {branch}; "
                "no branch would be closed."
            )

        print("Preview completed. No changes were made.")
        return

    for path in existing_files:
        run_git_command(f"git add {path}")

    run_git_command(f'git commit -am "{commit_msg}"')
    run_git_command(f'git tag -a {new_tag} -m "{tag_msg}"')
    run_git_command(f"git push origin {branch}")
    run_git_command("git push origin --tags")

    # Move 'latest' to the new release tag so the newest SemVer is always
    # marked as latest. This is best-effort and must not break the release.
    try:
        update_latest_tag(new_tag, preview=False)
    except GitError as exc:  # pragma: no cover
        print(
            f"[WARN] Failed to update floating 'latest' tag for {new_tag}: {exc}\n"
            "[WARN] The release itself completed successfully; only the "
            "'latest' tag was not updated."
        )

    print(f"Release {new_ver_str} completed.")

    if close:
        if branch in ("main", "master"):
            print(
                f"[INFO] close=True but current branch is {branch}; "
                "nothing to close."
            )
            return

        print(
            f"[INFO] Closing branch {branch} after successful release "
            "(close=True and branch is not main/master)..."
        )
        try:
            close_branch(name=branch, base_branch="main", cwd=".")
        except Exception as exc:  # pragma: no cover
            print(f"[WARN] Failed to close branch {branch} automatically: {exc}")


# ---------------------------------------------------------------------------
# Public release entry point
# ---------------------------------------------------------------------------


def release(
    pyproject_path: str = "pyproject.toml",
    changelog_path: str = "CHANGELOG.md",
    release_type: str = "patch",
    message: Optional[str] = None,
    preview: bool = False,
    force: bool = False,
    close: bool = False,
) -> None:
    """
    High-level release entry point.

    Modes:

    - preview=True:
        * Single-phase PREVIEW only.

    - preview=False, force=True:
        * Single-phase REAL release, no interactive preview.

    - preview=False, force=False:
        * Two-phase flow (intended default for interactive CLI use).
    """
    if preview:
        _release_impl(
            pyproject_path=pyproject_path,
            changelog_path=changelog_path,
            release_type=release_type,
            message=message,
            preview=True,
            close=close,
        )
        return

    if force:
        _release_impl(
            pyproject_path=pyproject_path,
            changelog_path=changelog_path,
            release_type=release_type,
            message=message,
            preview=False,
            close=close,
        )
        return

    if not sys.stdin.isatty():
        _release_impl(
            pyproject_path=pyproject_path,
            changelog_path=changelog_path,
            release_type=release_type,
            message=message,
            preview=False,
            close=close,
        )
        return

    print("[INFO] Running preview before actual release...\n")
    _release_impl(
        pyproject_path=pyproject_path,
        changelog_path=changelog_path,
        release_type=release_type,
        message=message,
        preview=True,
        close=close,
    )

    try:
        answer = input("Proceed with the actual release? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("\n[INFO] Release aborted (no confirmation).")
        return

    if answer not in ("y", "yes"):
        print("Release aborted by user. No changes were made.")
        return

    print("\n[INFO] Running REAL release...\n")
    _release_impl(
        pyproject_path=pyproject_path,
        changelog_path=changelog_path,
        release_type=release_type,
        message=message,
        preview=False,
        close=close,
    )


__all__ = ["release"]
