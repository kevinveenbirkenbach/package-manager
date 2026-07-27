from __future__ import annotations

import os
import re
import sys
from datetime import date

from .changelog_lint import (
    ChangelogLintError,
    lint_changelog_entry,
    transform_changelog_message,
)
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
    message: str | None = None,
    preview: bool = False,
) -> str:
    """Insert a new release entry into CHANGELOG.md.

    The entry is placed after the documents H1 heading (creating one if
    missing) and above any existing release entries, so the result stays
    markdown-lint-clean (MD041 first-line-h1, MD012 no-multiple-blanks).
    """
    today = date.today().isoformat()

    def _entry_for(raw: str) -> tuple[str, str]:
        body = transform_changelog_message(raw).strip() or f"Release {new_version}"
        return body, f"## [{new_version}] - {today}\n\n{body}\n\n"

    def _print_findings(findings: list[str]) -> None:
        print("\n[ERROR] Changelog entry is not markdown-lint clean:")
        for finding in findings:
            print(f"  - {finding}")
        print()

    if message is not None:
        body, entry = _entry_for(message)
        findings = lint_changelog_entry(changelog_path, entry)
        if findings:
            _print_findings(findings)
            raise ChangelogLintError(
                "Provided changelog message is not markdown-lint clean."
            )
    elif preview or not sys.stdin.isatty():
        body, entry = _entry_for(message or f"Release {new_version}")
    else:
        attempt: str | None = None
        while True:
            print(
                "\n[INFO] Provide the changelog entry — a leading '#' becomes "
                "bold, `code` becomes italic.\n"
            )
            raw = _open_editor_for_changelog(attempt)
            body, entry = _entry_for(raw or f"Release {new_version}")
            findings = lint_changelog_entry(changelog_path, entry)
            if not findings:
                break
            _print_findings(findings)
            attempt = body
            print("[INFO] Re-opening the editor so you can fix the entry...")

    changelog = ""
    if os.path.exists(changelog_path):
        try:
            with open(changelog_path, encoding="utf-8") as f:
                changelog = f.read()
        except (OSError, UnicodeDecodeError) as exc:
            print(f"[WARN] Could not read existing CHANGELOG.md: {exc}")

    new_changelog = _insert_after_h1(changelog, entry)

    print("\n================ CHANGELOG ENTRY ================")
    print(entry.rstrip())
    print("=================================================\n")

    if preview:
        print(f"[PREVIEW] Would insert new entry for {new_version} into CHANGELOG.md")
        return body

    with open(changelog_path, "w", encoding="utf-8") as f:
        f.write(new_changelog)

    print(f"Updated CHANGELOG.md with version {new_version}")
    return body
