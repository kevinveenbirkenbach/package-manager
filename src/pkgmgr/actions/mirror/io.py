from __future__ import annotations

import os
from urllib.parse import urlparse
from typing import Mapping

from .types import MirrorMap, Repository


def load_config_mirrors(repo: Repository) -> MirrorMap:
    mirrors = repo.get("mirrors") or {}
    result: MirrorMap = {}

    if isinstance(mirrors, dict):
        for name, url in mirrors.items():
            if url:
                result[str(name)] = str(url)
        return result

    if isinstance(mirrors, list):
        for entry in mirrors:
            if isinstance(entry, dict):
                name = entry.get("name")
                url = entry.get("url")
                if name and url:
                    result[str(name)] = str(url)

    return result


def read_mirrors_file(repo_dir: str, filename: str = "MIRRORS") -> MirrorMap:
    """
    Supports:
        NAME URL
        URL  → auto name = hostname
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

                # Case 1: "name url"
                if len(parts) == 2:
                    name, url = parts
                # Case 2: "url" → auto-generate name
                elif len(parts) == 1:
                    url = parts[0]
                    parsed = urlparse(url)
                    host = (parsed.netloc or "").split(":")[0]
                    base = host or "mirror"
                    name = base
                    i = 2
                    while name in mirrors:
                        name = f"{base}{i}"
                        i += 1
                else:
                    continue

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

    path = os.path.join(repo_dir, filename)
    lines = [f"{name} {url}" for name, url in sorted(mirrors.items())]
    content = "\n".join(lines) + ("\n" if lines else "")

    if preview:
        print(f"[PREVIEW] Would write MIRRORS file at {path}:")
        print(content or "(empty)")
        return

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        print(f"[INFO] Wrote MIRRORS file at {path}")
    except OSError as exc:
        print(f"[ERROR] Failed to write MIRRORS file at {path}: {exc}")
