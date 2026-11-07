from __future__ import annotations

import os

from pkgmgr.actions.branch.gc import _inside


def _mount(path: str) -> str:
    path = os.path.realpath(path)
    while not os.path.ismount(path):
        path = os.path.dirname(path)
    return path


def balance(paths: list[str], items: list[tuple[str, int]]) -> list[dict]:
    """
    Set what the report attributes against each filesystem's capacity.

    Args:
        paths: the roots and repository roots; each one's filesystem gets a row.
        items: (path, allocated bytes) of every listed entry; an entry inside
            another listed entry is counted only through the outer one.

    Returns:
        Per filesystem (grouped by st_dev): its mount point, total and free
        bytes (as available to unprivileged users) and the attributed bytes.
    """
    filesystems: dict[int, dict] = {}
    for path in paths:
        try:
            dev = os.stat(path).st_dev
            if dev in filesystems:
                continue
            vfs = os.statvfs(path)
        except OSError:
            continue
        filesystems[dev] = {
            "filesystem": _mount(path),
            "total_bytes": vfs.f_blocks * vfs.f_frsize,
            "free_bytes": vfs.f_bavail * vfs.f_frsize,
            "attributed_bytes": 0,
        }
    kept: list[str] = []
    for path, size in sorted((os.path.realpath(p), s) for p, s in items):
        if any(_inside(path, outer) for outer in kept):
            continue
        kept.append(path)
        try:
            dev = os.lstat(path).st_dev
        except OSError:
            continue
        if dev in filesystems:
            filesystems[dev]["attributed_bytes"] += size
    return sorted(filesystems.values(), key=lambda fs: fs["filesystem"])
