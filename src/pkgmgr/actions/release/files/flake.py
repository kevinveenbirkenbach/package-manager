from __future__ import annotations

import os
import re


def update_flake_version(
    flake_path: str, new_version: str, preview: bool = False
) -> None:
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
        lambda m: f"{m.group(1)}{new_version}{m.group(3)}",
        content,
    )

    if count == 0:
        print("[WARN] No version found in flake.nix.")
        return

    if preview:
        print(f"[PREVIEW] Would update flake.nix version to {new_version}")
        return

    with open(flake_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Updated flake.nix version to {new_version}")
