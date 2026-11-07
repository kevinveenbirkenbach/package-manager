from __future__ import annotations

import os
import stat

from .core_dumps import is_core_dump
from .walk import walk

CACHE_TAG = "CACHEDIR.TAG"
NODE_MODULES = "node_modules"


def _has(path: str, name: str, check=os.path.isfile) -> bool:
    return check(os.path.join(path, name))


def _kind(path: str, st: os.stat_result) -> str:
    name = os.path.basename(path)
    if not stat.S_ISDIR(st.st_mode):
        regular = stat.S_ISREG(st.st_mode)
        return "core-dump" if regular and is_core_dump(path) else "file"
    if name == NODE_MODULES:
        return "node_modules"
    if _has(path, ".git"):
        return "worktree"
    if _has(path, ".git", os.path.isdir) or (
        _has(path, "HEAD") and _has(path, "objects", os.path.isdir)
    ):
        return "git-repo"
    if _has(path, "pyvenv.cfg"):
        return "venv"
    if _has(path, CACHE_TAG) or name.lower().endswith("cache"):
        return "cache"
    return "dir"


def scan_root(root: str, threshold_bytes: int, cores: list[str]) -> dict:
    """
    Measure the direct children of one root on the root's own filesystem.

    Args:
        root: the directory to inventory.
        threshold_bytes: keep only children whose allocated size is above it.
        cores: receives the core dump candidates found while measuring.

    Returns:
        The root with its children over the threshold: path, kind, allocated
        size, newest mtime inside and unlistable directories, biggest first.

    Raises:
        OSError: when the root itself cannot be listed.
    """
    dev = os.stat(root).st_dev
    children: list[dict] = []
    with os.scandir(root) as entries:
        listing = sorted(entries, key=lambda entry: entry.name)
    for entry in listing:
        try:
            st = entry.stat(follow_symlinks=False)
        except OSError:
            continue
        if st.st_dev != dev:
            continue
        stats = walk(entry.path, dev)
        cores.extend(stats.cores)
        if stats.size_bytes > threshold_bytes:
            children.append(
                {
                    "path": entry.path,
                    "kind": _kind(entry.path, st),
                    "size_bytes": stats.size_bytes,
                    "newest_mtime": stats.newest_mtime,
                    "unreadable": stats.unreadable,
                }
            )
    children.sort(key=lambda child: (-child["size_bytes"], child["path"]))
    return {"root": root, "children": children}
