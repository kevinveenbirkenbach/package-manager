from __future__ import annotations

import os
import stat

ROOT_UID = 0
UID_MAP = "/proc/self/uid_map"
INITIAL_MAP = [[0, 0, 4294967295]]
OVERFLOW_UID = "/proc/sys/kernel/overflowuid"
SHARED_WRITE = stat.S_IWGRP | stat.S_IWOTH


def root_uids() -> frozenset[int]:
    """
    Returns:
        The owner uids that stand for root. In the initial user namespace,
        whose uid_map is the identity over every uid, that is 0. In any other
        namespace a mapped uid 0 may be any user, so only the overflow uid
        counts: the real root's files show up under it there, as do those of
        every other unmapped owner. Empty when a file it needs is unreadable
        or this process's own uid is unmapped, since its own files then show
        up as the overflow uid too.
    """
    try:
        with open(UID_MAP, encoding="ascii") as fh:
            ranges = [[int(n) for n in line.split()] for line in fh if line.strip()]
        if ranges == INITIAL_MAP:
            return frozenset({ROOT_UID})
        with open(OVERFLOW_UID, encoding="ascii") as fh:
            overflow = int(fh.read())
    except (OSError, ValueError):
        return frozenset()
    if os.geteuid() == overflow:
        return frozenset()
    return frozenset({overflow})


def root_resolved(path: str) -> str | None:
    """
    Args:
        path: an absolute file or directory.

    Returns:
        The path, resolved once, when it and every directory above it are
        owned by root and writable by neither group nor others, so no other
        user can replace what it names; None otherwise. Callers keep and use
        the returned path: resolving path again can follow a link swapped in
        after this check. In the initial user namespace a component on a
        nosuid mount also yields None: a desktop user can mount an image of
        root-owned files through udisks2 or FUSE, always nosuid, while the
        system's own directories never are; every bubblewrap mount is nosuid,
        so the rule cannot apply inside one.
    """
    owners = root_uids()
    initial = owners == {ROOT_UID}
    resolved = os.path.realpath(path)
    current = resolved
    while True:
        try:
            info = os.stat(current)
            nosuid = initial and os.statvfs(current).f_flag & os.ST_NOSUID
        except OSError:
            return None
        if info.st_uid not in owners or info.st_mode & SHARED_WRITE or nosuid:
            return None
        parent = os.path.dirname(current)
        if parent == current:
            return resolved
        current = parent


def trusted_path() -> str:
    """
    Returns:
        The PATH entries that resolve to root-controlled directories, else
        those of os.defpath, each in its resolved form and joined by
        os.pathsep, so a symbolic link another user can retarget never stays
        on it.

    Raises:
        RuntimeError: no entry of either qualifies; an empty PATH would make
            the hook search its working directory, the worktree.
    """
    for source in (os.get_exec_path(), os.defpath.split(os.pathsep)):
        resolved = (root_resolved(entry) for entry in source if os.path.isabs(entry))
        entries = dict.fromkeys(
            entry for entry in resolved if entry and os.path.isdir(entry)
        )
        if entries:
            return os.pathsep.join(entries)
    raise RuntimeError(
        "no PATH entry is a root-owned directory closed to other writers"
    )
