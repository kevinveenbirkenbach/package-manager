#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File and metadata update helpers for the release workflow.

Responsibilities:
  - Update pyproject.toml with the new version.
  - Update flake.nix, PKGBUILD, RPM spec files where present.
  - Prepend release entries to CHANGELOG.md.
  - Maintain distribution-specific changelog files:
      * debian/changelog
      * RPM spec %changelog section
    including maintainer metadata where applicable.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from datetime import date, datetime
from typing import Optional, Tuple

from pkgmgr.core.git.queries import get_config_value


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

    lines = [line for line in content.splitlines() if not line.strip().startswith("#")]
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

    If the file does not exist, it is skipped without failing the release.
    """
    if not os.path.exists(pyproject_path):
        print(
            f"[INFO] pyproject.toml not found at: {pyproject_path}, "
            "skipping version update."
        )
        return

    try:
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as exc:
        print(
            f"[WARN] Could not read pyproject.toml at {pyproject_path}: {exc}. "
            "Skipping version update."
        )
        return

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
            "[PREVIEW] Would update spec file "
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
        name = get_config_value("user.name")
    if not email:
        email = get_config_value("user.email")

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
# Fedora / RPM spec %changelog helper
# ---------------------------------------------------------------------------


def update_spec_changelog(
    spec_path: str,
    package_name: str,
    new_version: str,
    message: Optional[str] = None,
    preview: bool = False,
) -> None:
    """
    Prepend a new entry to the %changelog section of an RPM spec file,
    if present.

    Typical RPM-style entry:

        * Tue Dec 09 2025 John Doe <john@example.com> - 0.5.1-1
        - Your changelog message
    """
    if not os.path.exists(spec_path):
        print("[INFO] RPM spec file not found, skipping spec changelog update.")
        return

    try:
        with open(spec_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as exc:
        print(f"[WARN] Could not read spec file for changelog update: {exc}")
        return

    debian_version = f"{new_version}-1"
    now = datetime.now().astimezone()
    date_str = now.strftime("%a %b %d %Y")

    # Reuse Debian maintainer discovery for author name/email.
    author_name, author_email = _get_debian_author()

    body_line = message.strip() if message else f"Automated release {new_version}."

    stanza = (
        f"* {date_str} {author_name} <{author_email}> - {debian_version}\n"
        f"- {body_line}\n\n"
    )

    marker = "%changelog"
    idx = content.find(marker)

    if idx == -1:
        # No %changelog section yet: append one at the end.
        new_content = content.rstrip() + "\n\n%changelog\n" + stanza
    else:
        # Insert stanza right after the %changelog line.
        before = content[: idx + len(marker)]
        after = content[idx + len(marker) :]
        new_content = before + "\n" + stanza + after.lstrip("\n")

    if preview:
        print(
            "[PREVIEW] Would update RPM %changelog section with the following "
            "stanza:\n"
            f"{stanza}"
        )
        return

    try:
        with open(spec_path, "w", encoding="utf-8") as f:
            f.write(new_content)
    except Exception as exc:
        print(f"[WARN] Failed to write updated spec changelog section: {exc}")
        return

    print(
        f"Updated RPM %changelog section in {os.path.basename(spec_path)} "
        f"for {package_name} {debian_version}"
    )
