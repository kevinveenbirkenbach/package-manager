from __future__ import annotations

import os
import re
import stat
from dataclasses import dataclass, field

BLOCK = 512
CORE_NAME = re.compile(r"core(\.\d+)?")


@dataclass
class TreeStats:
    size_bytes: int = 0
    newest_mtime: float = 0.0
    foreign_entries: int = 0
    unreadable: int = 0
    cores: list[str] = field(default_factory=list)


def is_foreign(path: str, st: os.stat_result) -> bool:
    return st.st_uid != os.getuid()


def _account(
    stats: TreeStats, path: str, st: os.stat_result, seen: set[tuple[int, int]]
) -> None:
    if st.st_nlink > 1 and not stat.S_ISDIR(st.st_mode):
        if (st.st_dev, st.st_ino) in seen:
            return
        seen.add((st.st_dev, st.st_ino))
    stats.size_bytes += st.st_blocks * BLOCK
    stats.newest_mtime = max(stats.newest_mtime, st.st_mtime)
    if stat.S_ISREG(st.st_mode) and CORE_NAME.fullmatch(os.path.basename(path)):
        stats.cores.append(path)


def _children(path: str, stats: TreeStats) -> list[os.DirEntry]:
    try:
        with os.scandir(path) as entries:
            return list(entries)
    except OSError:
        stats.unreadable += 1
        return []


def walk(path: str, dev: int | None = None) -> TreeStats:
    """
    Measure a tree like `du -x`: allocated blocks, symlinks never followed.

    Args:
        path: the tree root, measured itself as well.
        dev: the filesystem (st_dev) to stay on; that of path when None.

    Returns:
        Allocated bytes (st_blocks * 512, each hard-linked inode once), the
        newest mtime, entries not owned by the current uid (none counted below a
        foreign one), directories that could not be listed, and the regular
        files named `core` or `core.<digits>`.
    """
    stats = TreeStats()
    try:
        top = os.lstat(path)
    except OSError:
        stats.unreadable += 1
        return stats
    dev = top.st_dev if dev is None else dev
    if top.st_dev != dev:
        return stats
    seen: set[tuple[int, int]] = set()
    stack: list[tuple[str, os.stat_result, bool]] = [(path, top, False)]
    while stack:
        current, st, pruned = stack.pop()
        _account(stats, current, st, seen)
        foreign = not pruned and is_foreign(current, st)
        stats.foreign_entries += foreign
        if not stat.S_ISDIR(st.st_mode):
            continue
        for entry in _children(current, stats):
            try:
                child = entry.stat(follow_symlinks=False)
            except OSError:
                continue
            if child.st_dev == dev:
                stack.append((entry.path, child, pruned or foreign))
    return stats
