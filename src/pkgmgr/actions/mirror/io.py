from __future__ import annotations

import os
from typing import List, Mapping

from .types import MirrorMap, Repository


def load_config_mirrors(repo: Repository) -> MirrorMap:
    """
    Load mirrors from the repository configuration entry.

    Supported shapes:

      repo["mirrors"] = {
          "origin": "ssh://git@example.com/...",
          "backup": "ssh://git@backup/...",
      }

      or

      repo["mirrors"] = [
          {"name": "origin", "url": "ssh://git@example.com/..."},
          {"name": "backup", "url": "ssh://git@backup/..."},
      ]
    """
    mirrors = repo.get("mirrors") or {}
    result: MirrorMap = {}

    if isinstance(mirrors, dict):
        for name, url in mirrors.items():
            if not url:
                continue
            result[str(name)] = str(url)
        return result

    if isinstance(mirrors, list):
        for entry in mirrors:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name")
            url = entry.get("url")
            if not name or not url:
                continue
            result[str(name)] = str(url)

    return result


def read_mirrors_file(repo_dir: str, filename: str = "MIRRORS") -> MirrorMap:
    """
    Read mirrors from the MIRRORS file in the repository directory.

    Simple text format:

        # comment
        origin  ssh://git@example.com/account/repo.git
        backup  ssh://git@backup/account/repo.git
    """
    path = os.path.join(repo_dir, filename)
    mirrors: MirrorMap = {}

    if not os.path.exists(path):
        return mirrors

    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                parts = stripped.split(None, 1)
                if len(parts) != 2:
                    # Ignore malformed lines silently
                    continue
                name, url = parts
                mirrors[name] = url
    except OSError as exc:
        print(f"[WARN] Could not read MIRRORS file at {path}: {exc}")

    return mirrors


def write_mirrors_file(
    repo_dir: str,
    mirrors: Mapping[str, str],
    filename: str = "MIRRORS",
    preview: bool = False,
) -> None:
    """
    Write mirrors to MIRRORS file.

    Existing file is overwritten. In preview mode we only print what would
    be written.
    """
    path = os.path.join(repo_dir, filename)
    lines: List[str] = [f"{name} {url}" for name, url in sorted(mirrors.items())]
    content = "\n".join(lines) + ("\n" if lines else "")

    if preview:
        print(f"[PREVIEW] Would write MIRRORS file at {path}:")
        if content:
            print(content.rstrip())
        else:
            print("(empty)")
        return

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        print(f"[INFO] Wrote MIRRORS file at {path}")
    except OSError as exc:
        print(f"[ERROR] Failed to write MIRRORS file at {path}: {exc}")
