from __future__ import annotations

import os
from datetime import datetime
from typing import Optional

from .debian import _get_debian_author


def update_spec_changelog(
    spec_path: str,
    package_name: str,
    new_version: str,
    message: Optional[str] = None,
    preview: bool = False,
) -> None:
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

    author_name, author_email = _get_debian_author()
    body_line = message.strip() if message else f"Automated release {new_version}."

    stanza = (
        f"* {date_str} {author_name} <{author_email}> - {debian_version}\n"
        f"- {body_line}\n\n"
    )

    marker = "%changelog"
    idx = content.find(marker)

    if idx == -1:
        new_content = content.rstrip() + "\n\n%changelog\n" + stanza
    else:
        before = content[: idx + len(marker)]
        after = content[idx + len(marker) :]
        new_content = before + "\n" + stanza + after.lstrip("\n")

    if preview:
        print(
            "[PREVIEW] Would update RPM %changelog section with the following stanza:\n"
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
