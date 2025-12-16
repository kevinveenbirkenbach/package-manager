from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from typing import Union
from urllib.parse import urlparse

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
        URL  -> auto-generate name from hostname
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

                # Case 2: "url" -> auto name
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


MirrorsInput = Union[Mapping[str, str], Iterable[str]]


def write_mirrors_file(
    repo_dir: str,
    mirrors: MirrorsInput,
    filename: str = "MIRRORS",
    preview: bool = False,
) -> None:
    """
    Write MIRRORS in one of two formats:

    1) Mapping[str, str] -> "NAME URL" per line (legacy / compatible)
    2) Iterable[str]     -> "URL" per line (new preferred)

    Strings are treated as a single URL (not iterated character-by-character).
    """
    path = os.path.join(repo_dir, filename)

    lines: list[str]

    if isinstance(mirrors, Mapping):
        items = [
            (str(name), str(url))
            for name, url in mirrors.items()
            if url is not None and str(url).strip()
        ]
        items.sort(key=lambda x: (x[0], x[1]))
        lines = [f"{name} {url}" for name, url in items]

    else:
        if isinstance(mirrors, (str, bytes)):
            urls = [str(mirrors).strip()]
        else:
            urls = [
                str(url).strip()
                for url in mirrors
                if url is not None and str(url).strip()
            ]

        urls = sorted(set(urls))
        lines = urls

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
