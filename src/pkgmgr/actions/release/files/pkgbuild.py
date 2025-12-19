from __future__ import annotations

import os
import re


def update_pkgbuild_version(
    pkgbuild_path: str, new_version: str, preview: bool = False
) -> None:
    if not os.path.exists(pkgbuild_path):
        print("[INFO] PKGBUILD not found, skipping.")
        return

    try:
        with open(pkgbuild_path, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as exc:
        print(f"[WARN] Could not read PKGBUILD: {exc}")
        return

    content, _ = re.subn(
        r"^(pkgver\s*=\s*)(.+)$",
        lambda m: f"{m.group(1)}{new_version}",
        content,
        flags=re.MULTILINE,
    )
    content, _ = re.subn(
        r"^(pkgrel\s*=\s*)(.+)$",
        lambda m: f"{m.group(1)}1",
        content,
        flags=re.MULTILINE,
    )

    if preview:
        print(f"[PREVIEW] Would update PKGBUILD to pkgver={new_version}, pkgrel=1")
        return

    with open(pkgbuild_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"Updated PKGBUILD to pkgver={new_version}, pkgrel=1")
