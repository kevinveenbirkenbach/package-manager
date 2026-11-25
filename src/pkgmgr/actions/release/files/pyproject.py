from __future__ import annotations

import os
import re

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

from pkgmgr.core.version.source import dynamic_version_source, version_literal


def update_module_version(
    path: str, name: str, new_version: str, preview: bool
) -> None:
    """
    Args:
        path: the module file that holds the version literal.
        name: the attribute assigned the version, e.g. __version__.
        new_version: the version to write.
        preview: print the change instead of writing it.

    Raises:
        RuntimeError: the file holds no `name = "..."` literal.
    """
    with open(path, encoding="utf-8") as f:
        content = f.read()
    new_content, count = version_literal(name).subn(
        lambda mm: f"{mm.group(1)}{new_version}{mm.group(3)}", content, count=1
    )
    if count == 0:
        raise RuntimeError(f"Missing {name} literal in {path}")
    if preview:
        print(f"[PREVIEW] Would update {name} in {path} to {new_version}")
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Updated {name} in {path} to {new_version}")


def update_pyproject_version(
    pyproject_path: str, new_version: str, preview: bool = False
) -> None:
    if not os.path.exists(pyproject_path):
        print(f"[INFO] pyproject.toml not found at: {pyproject_path}, skipping.")
        return

    try:
        with open(pyproject_path, encoding="utf-8") as f:
            content = f.read()
    except OSError as exc:
        print(f"[WARN] Could not read pyproject.toml: {exc}")
        return

    data = tomllib.loads(content)
    project = data.get("project")
    source = dynamic_version_source(pyproject_path, data)
    if source is not None:
        update_module_version(*source, new_version, preview)
        return
    if project is None or "version" in project.get("dynamic", []):
        print("[INFO] pyproject.toml declares no static version, skipping.")
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
