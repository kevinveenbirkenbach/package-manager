from __future__ import annotations

import os
import re


def update_spec_version(
    spec_path: str, new_version: str, preview: bool = False
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

    def _release_repl(m: re.Match[str]) -> str:
        rest = m.group(2).strip()
        match = re.match(r"^(\d+)(.*)$", rest)
        suffix = match.group(2) if match else ""
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
