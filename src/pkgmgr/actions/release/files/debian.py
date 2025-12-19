from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, Tuple

from pkgmgr.core.git.queries import get_config_value


def _get_debian_author() -> Tuple[str, str]:
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

    with open(debian_changelog_path, "w", encoding="utf-8") as f:
        f.write(stanza + existing)

    print(f"Updated debian/changelog with version {debian_version}")
