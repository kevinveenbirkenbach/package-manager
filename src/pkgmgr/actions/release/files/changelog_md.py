from __future__ import annotations

import os
import re
from datetime import date
from typing import Optional

from .editor import _open_editor_for_changelog

H1_RE = re.compile(r"^#\s+\S", re.MULTILINE)
H2_RE = re.compile(r"^##\s+\S", re.MULTILINE)


def _insert_after_h1(existing: str, entry: str) -> str:
    """Place *entry* after the H1 (and any intro prose), above the first H2.

    If the file has no H1 we synthesise ``# Changelog`` so the resulting
    document is markdown-lint-clean (MD041 first-line-h1).
    If the file has no H2 yet we append *entry* after the H1 block.
    Existing behaviour for legacy headerless files (file starts with
    ``## ``) is preserved: *entry* is prepended unchanged.
    """
    if not existing.strip():
        return f"# Changelog\n\n{entry}"

    if not H1_RE.search(existing):
        # Legacy layout: file starts with `## [version]` and has no H1.
        # Synthesise the H1 so the merged file is lint-clean.
        return f"# Changelog\n\n{entry}{existing.lstrip()}"

    # File has an H1. Find the first H2 (existing release section).
    h2_match = H2_RE.search(existing)
    if h2_match is None:
        # H1 + optional intro but no release entries yet — append entry
        # after a single blank line.
        suffix = (
            ""
            if existing.endswith("\n\n")
            else ("\n" if existing.endswith("\n") else "\n\n")
        )
        return f"{existing}{suffix}{entry}"

    # Insert new entry just before the first H2.
    head = existing[: h2_match.start()].rstrip("\n") + "\n\n"
    tail = existing[h2_match.start() :]
    return f"{head}{entry}{tail}"


def update_changelog(
    changelog_path: str,
    new_version: str,
    message: Optional[str] = None,
    preview: bool = False,
) -> str:
    """Insert a new release entry into CHANGELOG.md.

    The entry is placed after the documents H1 heading (creating one if
    missing) and above any existing release entries, so the result stays
    markdown-lint-clean (MD041 first-line-h1, MD012 no-multiple-blanks).
    """
    today = date.today().isoformat()

    if message is None:
        if preview:
            message = "Automated release."
        else:
            print(
                "\n[INFO] No release message provided, opening editor for changelog entry...\n"
            )
            editor_message = _open_editor_for_changelog()
            if not editor_message:
                message = "Automated release."
            else:
                message = editor_message

    body = message.strip() if message and message.strip() else f"Release {new_version}."
    entry = f"## [{new_version}] - {today}\n\n{body}\n\n"

    if os.path.exists(changelog_path):
        try:
            with open(changelog_path, "r", encoding="utf-8") as f:
                changelog = f.read()
        except Exception as exc:
            print(f"[WARN] Could not read existing CHANGELOG.md: {exc}")
            changelog = ""
    else:
        changelog = ""

    new_changelog = _insert_after_h1(changelog, entry)

    print("\n================ CHANGELOG ENTRY ================")
    print(entry.rstrip())
    print("=================================================\n")

    if preview:
        print(f"[PREVIEW] Would insert new entry for {new_version} into CHANGELOG.md")
        return message

    with open(changelog_path, "w", encoding="utf-8") as f:
        f.write(new_changelog)

    print(f"Updated CHANGELOG.md with version {new_version}")
    return message
