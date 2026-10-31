from __future__ import annotations

import os
import re


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def _write(path: str, content: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def update_cargo_version(
    repo_root: str, new_version: str, preview: bool = False
) -> list[str]:
    """
    Set the root crate's version in Cargo.toml and its entry in Cargo.lock.

    Args:
        repo_root: repository root that may hold Cargo.toml and Cargo.lock.
        new_version: release version without the leading "v".
        preview: only print what would change.

    Returns:
        The paths that were (or in preview would be) changed.
    """
    toml_path = os.path.join(repo_root, "Cargo.toml")
    if not os.path.exists(toml_path):
        print("[INFO] No Cargo.toml found. Skipping Cargo version update.")
        return []

    toml = _read(toml_path)
    block = re.search(r"(?ms)^\[package\]\s*$.*?(?=^\s*\[|\Z)", toml)
    if not block:
        print("[INFO] Cargo.toml has no [package] section. Skipping.")
        return []

    name = re.search(r'(?m)^\s*name\s*=\s*"([^"]+)"', block.group(0))
    if not name:
        raise RuntimeError("Missing name key in [package] section of Cargo.toml")
    new_block, count = re.subn(
        r'(?m)^(\s*version\s*=\s*")[^"]+(")',
        lambda m: f"{m.group(1)}{new_version}{m.group(2)}",
        block.group(0),
        count=1,
    )
    if count == 0:
        raise RuntimeError("Missing version key in [package] section of Cargo.toml")
    changes = {toml_path: toml[: block.start()] + new_block + toml[block.end() :]}

    lock_path = os.path.join(repo_root, "Cargo.lock")
    if os.path.exists(lock_path):
        lock, count = re.subn(
            rf'(?m)^(\[\[package\]\]\nname = "{re.escape(name.group(1))}"\n'
            r'version = ")[^"]+("\n)(?!source = )',
            lambda m: f"{m.group(1)}{new_version}{m.group(2)}",
            _read(lock_path),
        )
        if count != 1:
            raise RuntimeError(
                f"Expected one local {name.group(1)!r} package in Cargo.lock, "
                f"found {count}"
            )
        changes[lock_path] = lock

    for path, content in changes.items():
        if preview:
            print(f"[PREVIEW] Would update {path} version to {new_version}")
        else:
            _write(path, content)
            print(f"Updated {path} version to {new_version}")
    return list(changes)
