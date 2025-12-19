from __future__ import annotations

import os
import re


def update_pyproject_version(
    pyproject_path: str, new_version: str, preview: bool = False
) -> None:
    if not os.path.exists(pyproject_path):
        print(f"[INFO] pyproject.toml not found at: {pyproject_path}, skipping.")
        return

    try:
        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError as exc:
        print(f"[WARN] Could not read pyproject.toml: {exc}")
        return

    m = re.search(r"(?ms)^\s*\[project\]\s*$.*?(?=^\s*\[|\Z)", content)
    if not m:
        raise RuntimeError("Missing [project] section in pyproject.toml")

    project_block = m.group(0)
    ver_pat = r'(?m)^(\s*version\s*=\s*")([^"]+)(")\s*$'

    new_block, count = re.subn(
        ver_pat,
        lambda mm: f"{mm.group(1)}{new_version}{mm.group(3)}",
        project_block,
    )
    if count == 0:
        raise RuntimeError("Missing version key in [project] section")

    new_content = content[: m.start()] + new_block + content[m.end() :]

    if preview:
        print(f"[PREVIEW] Would update pyproject.toml version to {new_version}")
        return

    with open(pyproject_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Updated pyproject.toml version to {new_version}")
