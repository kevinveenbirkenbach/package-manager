# pkgmgr/release.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
pkgmgr/release.py

Release helper for pkgmgr.

Responsibilities (Milestone 7):
  - Determine the next semantic version based on existing Git tags.
  - Update pyproject.toml with the new version.
  - Update additional packaging files (flake.nix, PKGBUILD,
    debian/changelog, RPM spec) where present.
  - Prepend a basic entry to CHANGELOG.md.
  - Commit, tag, and push the release on the current branch.

Additional behaviour:
  - If `preview=True` (from --preview), no files are written and no
    Git commands are executed. Instead, a detailed summary of the
    planned changes and commands is printed.
  - If `preview=False` and not forced, the release is executed in two
    phases:
      1) Preview-only run (dry-run).
      2) Interactive confirmation, then real release if confirmed.
    This confirmation can be skipped with the `force=True` flag.
  - If `close=True` is used and the current branch is not main/master,
    the branch will be closed via branch_commands.close_branch() after
    a successful release.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from datetime import date, datetime
from typing import Optional, Tuple

from pkgmgr.git_utils import get_tags, get_current_branch, GitError
from pkgmgr.branch_commands import close_branch
from pkgmgr.versioning import (
    SemVer,
    find_latest_version,
    bump_major,
    bump_minor,
    bump_patch,
)


# ---------------------------------------------------------------------------
# Helpers for Git + version discovery
# ---------------------------------------------------------------------------


def _determine_current_version() -> SemVer:
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


def _bump_semver(current: SemVer, release_type: str) -> SemVer:
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


# ---------------------------------------------------------------------------
# Low-level Git command helper
# ---------------------------------------------------------------------------


def _run_git_command(cmd: str) -> None:
    """
    Run a Git (or shell) command with basic error reporting.

    The command is executed via the shell, primarily for readability
    when printed (as in 'git commit -am "msg"').
    """
    print(f"[GIT] {cmd}")
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] Git command failed: {cmd}")
        print(f"        Exit code: {exc.returncode}")
        if exc.stdout:
            print("--- stdout ---")
            print(exc.stdout)
        if exc.stderr:
            print("--- stderr ---")
            print(exc.stderr)
        raise GitError(f"Git command failed: {cmd}") from exc


# ---------------------------------------------------------------------------
# Editor helper for interactive changelog messages
# ---------------------------------------------------------------------------


def _open_editor_for_changelog(initial_message: Optional[str] = None) -> str:
    """
    Open $EDITOR (fallback 'nano') so the user can enter a changelog message.

    The temporary file is pre-filled with commented instructions and an
    optional initial_message. Lines starting with '#' are ignored when the
    message is read back.

    Returns the final message (may be empty string if user leaves it blank).
    """
    editor = os.environ.get("EDITOR", "nano")

    with tempfile.NamedTemporaryFile(
        mode="w+",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp_path = tmp.name
        tmp.write(
            "# Write the changelog entry for this release.\n"
            "# Lines starting with '#' will be ignored.\n"
            "# Empty result will fall back to a generic message.\n\n"
        )
        if initial_message:
            tmp.write(initial_message.strip() + "\n")
        tmp.flush()

    try:
        subprocess.call([editor, tmp_path])
    except FileNotFoundError:
        print(
            f"[WARN] Editor {editor!r} not found; proceeding without "
            "interactive changelog message."
        )

    try:
        with open(tmp_path, "r", encoding="utf-8") as f:
            content = f.read()
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    lines = [
        line for line in content.splitlines()
        if not line.strip().startswith("#")
    ]
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# File update helpers (pyproject + extra packaging + changelog)
# ---------------------------------------------------------------------------


def update_pyproject_version(
    pyproject_path: str,
    new_version: str,
    preview: bool = False,
) -> None:
    """
    Update the version in pyproject.toml with the new version.

    The function looks for a line matching:

        version = "X.Y.Z"

    and replaces the version part with the given new_version string.
    """
    try:
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print(f"[ERROR] pyproject.toml not found at: {pyproject_path}")
        sys.exit(1)

    pattern = r'^(version\s*=\s*")([^"]+)(")'
    new_content, count = re.subn(
        pattern,
        lambda m: f'{m.group(1)}{new_version}{m.group(3)}',
        content,
        flags=re.MULTILINE,
    )

    if count == 0:
        print("[ERROR] Could not find version line in pyproject.toml")
        sys.exit(1)

    if preview:
        print(f"[PREVIEW] Would update pyproject.toml version to {new_version}")
        return

    with open(pyproject_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Updated pyproject.toml version to {new_version}")


def update_flake_version(
    flake_path: str,
    new_version: str,
    preview: bool = False,
) -> None:
    """
    Update the version in flake.nix, if present.
    """
    if not os.path.exists(flake_path):
        print("[INFO] flake.nix not found, skipping.")
        return

    try:
        with open(flake_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as exc:
        print(f"[WARN] Could not read flake.nix: {exc}")
        return

    pattern = r'(version\s*=\s*")([^"]+)(")'
    new_content, count = re.subn(
        pattern,
        lambda m: f'{m.group(1)}{new_version}{m.group(3)}',
        content,
    )

    if count == 0:
        print("[WARN] No version assignment found in flake.nix, skipping.")
        return

    if preview:
        print(f"[PREVIEW] Would update flake.nix version to {new_version}")
        return

    with open(flake_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Updated flake.nix version to {new_version}")


def update_pkgbuild_version(
    pkgbuild_path: str,
    new_version: str,
    preview: bool = False,
) -> None:
    """
    Update the version in PKGBUILD, if present.

    Expects:
        pkgver=1.2.3
        pkgrel=1
    """
    if not os.path.exists(pkgbuild_path):
        print("[INFO] PKGBUILD not found, skipping.")
        return

    try:
        with open(pkgbuild_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as exc:
        print(f"[WARN] Could not read PKGBUILD: {exc}")
        return

    ver_pattern = r"^(pkgver\s*=\s*)(.+)$"
    new_content, ver_count = re.subn(
        ver_pattern,
        lambda m: f"{m.group(1)}{new_version}",
        content,
        flags=re.MULTILINE,
    )

    if ver_count == 0:
        print("[WARN] No pkgver line found in PKGBUILD.")
        new_content = content

    rel_pattern = r"^(pkgrel\s*=\s*)(.+)$"
    new_content, rel_count = re.subn(
        rel_pattern,
        lambda m: f"{m.group(1)}1",
        new_content,
        flags=re.MULTILINE,
    )

    if rel_count == 0:
        print("[WARN] No pkgrel line found in PKGBUILD.")

    if preview:
        print(f"[PREVIEW] Would update PKGBUILD to pkgver={new_version}, pkgrel=1")
        return

    with open(pkgbuild_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Updated PKGBUILD to pkgver={new_version}, pkgrel=1")


def update_spec_version(
    spec_path: str,
    new_version: str,
    preview: bool = False,
) -> None:
    """
    Update the version in an RPM spec file, if present.
    """
    if not os.path.exists(spec_path):
        print("[INFO] RPM spec file not found, skipping.")
        return

    try:
        with open(spec_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as exc:
        print(f"[WARN] Could not read spec file: {exc}")
        return

    ver_pattern = r"^(Version:\s*)(.+)$"
    new_content, ver_count = re.subn(
        ver_pattern,
        lambda m: f"{m.group(1)}{new_version}",
        content,
        flags=re.MULTILINE,
    )

    if ver_count == 0:
        print("[WARN] No 'Version:' line found in spec file.")

    rel_pattern = r"^(Release:\s*)(.+)$"

    def _release_repl(m: re.Match[str]) -> str:  # type: ignore[name-defined]
        rest = m.group(2).strip()
        match = re.match(r"^(\d+)(.*)$", rest)
        if match:
            suffix = match.group(2)
        else:
            suffix = ""
        return f"{m.group(1)}1{suffix}"

    new_content, rel_count = re.subn(
        rel_pattern,
        _release_repl,
        new_content,
        flags=re.MULTILINE,
    )

    if rel_count == 0:
        print("[WARN] No 'Release:' line found in spec file.")

    if preview:
        print(
            f"[PREVIEW] Would update spec file "
            f"{os.path.basename(spec_path)} to Version: {new_version}, Release: 1..."
        )
        return

    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(
        f"Updated spec file {os.path.basename(spec_path)} "
        f"to Version: {new_version}, Release: 1..."
    )


def update_changelog(
    changelog_path: str,
    new_version: str,
    message: Optional[str] = None,
    preview: bool = False,
) -> str:
    """
    Prepend a new release section to CHANGELOG.md with the new version,
    current date, and a message.
    """
    today = date.today().isoformat()

    if message is None:
        if preview:
            message = "Automated release."
        else:
            print(
                "\n[INFO] No release message provided, opening editor for "
                "changelog entry...\n"
            )
            editor_message = _open_editor_for_changelog()
            if not editor_message:
                message = "Automated release."
            else:
                message = editor_message

    header = f"## [{new_version}] - {today}\n"
    header += f"\n* {message}\n\n"

    if os.path.exists(changelog_path):
        try:
            with open(changelog_path, "r", encoding="utf-8") as f:
                changelog = f.read()
        except Exception as exc:
            print(f"[WARN] Could not read existing CHANGELOG.md: {exc}")
            changelog = ""
    else:
        changelog = ""

    new_changelog = header + "\n" + changelog if changelog else header

    print("\n================ CHANGELOG ENTRY ================")
    print(header.rstrip())
    print("=================================================\n")

    if preview:
        print(f"[PREVIEW] Would prepend new entry for {new_version} to CHANGELOG.md")
        return message

    with open(changelog_path, "w", encoding="utf-8") as f:
        f.write(new_changelog)

    print(f"Updated CHANGELOG.md with version {new_version}")

    return message


# ---------------------------------------------------------------------------
# Debian changelog helpers (with Git config fallback for maintainer)
# ---------------------------------------------------------------------------


def _get_git_config_value(key: str) -> Optional[str]:
    """
    Try to read a value from `git config --get <key>`.
    """
    try:
        result = subprocess.run(
            ["git", "config", "--get", key],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return None

    value = result.stdout.strip()
    return value or None


def _get_debian_author() -> Tuple[str, str]:
    """
    Determine the maintainer name/email for debian/changelog entries.
    """
    name = os.environ.get("DEBFULLNAME")
    email = os.environ.get("DEBEMAIL")

    if not name:
        name = os.environ.get("GIT_AUTHOR_NAME")
    if not email:
        email = os.environ.get("GIT_AUTHOR_EMAIL")

    if not name:
        name = _get_git_config_value("user.name")
    if not email:
        email = _get_git_config_value("user.email")

    if not name:
        name = "Unknown Maintainer"
    if not email:
        email = "unknown@example.com"

    return name, email


def update_debian_changelog(
    debian_changelog_path: str,
    package_name: str,
    new_version: str,
    message: Optional[str] = None,
    preview: bool = False,
) -> None:
    """
    Prepend a new entry to debian/changelog, if it exists.
    """
    if not os.path.exists(debian_changelog_path):
        print("[INFO] debian/changelog not found, skipping.")
        return

    debian_version = f"{new_version}-1"
    now = datetime.now().astimezone()
    date_str = now.strftime("%a, %d %b %Y %H:%M:%S %z")

    author_name, author_email = _get_debian_author()

    first_line = f"{package_name} ({debian_version}) unstable; urgency=medium"
    body_line = message.strip() if message else f"Automated release {new_version}."
    stanza = (
        f"{first_line}\n\n"
        f"  * {body_line}\n\n"
        f" -- {author_name} <{author_email}>  {date_str}\n\n"
    )

    if preview:
        print(
            "[PREVIEW] Would prepend the following stanza to debian/changelog:\n"
            f"{stanza}"
        )
        return

    try:
        with open(debian_changelog_path, "r", encoding="utf-8") as f:
            existing = f.read()
    except Exception as exc:
        print(f"[WARN] Could not read debian/changelog: {exc}")
        existing = ""

    new_content = stanza + existing

    with open(debian_changelog_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Updated debian/changelog with version {debian_version}")


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
    current_ver = _determine_current_version()
    new_ver = _bump_semver(current_ver, release_type)
    new_ver_str = str(new_ver)
    new_tag = new_ver.to_tag(with_prefix=True)

    mode = "PREVIEW" if preview else "REAL"
    print(f"Release mode: {mode}")
    print(f"Current version: {current_ver}")
    print(f"New version:     {new_ver_str} ({release_type})")

    repo_root = os.path.dirname(os.path.abspath(pyproject_path))

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

    try:
        branch = get_current_branch() or "main"
    except GitError:
        branch = "main"
    print(f"Releasing on branch: {branch}")

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
        _run_git_command(f"git add {path}")

    _run_git_command(f'git commit -am "{commit_msg}"')
    _run_git_command(f'git tag -a {new_tag} -m "{tag_msg}"')
    _run_git_command(f"git push origin {branch}")
    _run_git_command("git push origin --tags")

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
