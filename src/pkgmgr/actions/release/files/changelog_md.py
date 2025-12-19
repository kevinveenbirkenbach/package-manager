from __future__ import annotations

import os
from datetime import date
from typing import Optional

from .editor import _open_editor_for_changelog


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
                "\n[INFO] No release message provided, opening editor for changelog entry...\n"
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
