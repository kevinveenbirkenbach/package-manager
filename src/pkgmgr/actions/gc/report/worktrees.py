from __future__ import annotations

import os

from pkgmgr.actions.branch.gc import _worktrees

from .walk import TreeStats, walk

AGENT_DIR = os.path.join(".claude", "worktrees")
AGENT_PREFIX = "agent-"
METADATA_FILES = ("index", "HEAD")


def _metadata_mtime(path: str) -> float:
    try:
        with open(os.path.join(path, ".git"), encoding="utf-8") as fh:
            gitdir = fh.read().strip().removeprefix("gitdir: ")
    except OSError:
        return 0.0
    meta = os.path.normpath(os.path.join(path, gitdir))
    stamps = [0.0]
    for name in METADATA_FILES:
        try:
            stamps.append(os.stat(os.path.join(meta, name)).st_mtime)
        except OSError:
            continue
    return max(stamps)


def _record(
    repo: str,
    path: str,
    branch: str | None,
    head: str | None,
    orphaned: bool,
    cores: list[str],
) -> dict:
    present = os.path.isdir(path)
    stats = walk(path) if present else TreeStats()
    cores.extend(stats.cores)
    activity = max(stats.newest_mtime, _metadata_mtime(path)) if present else 0.0
    return {
        "repo": repo,
        "path": path,
        "branch": branch,
        "head": head,
        "orphaned": orphaned,
        "missing": not present,
        "size_bytes": stats.size_bytes if present else None,
        "last_activity": activity or None,
        "foreign_entries": stats.foreign_entries,
        "unreadable": stats.unreadable,
    }


def _agent_dirs(repo: str) -> list[str]:
    base = os.path.join(repo, AGENT_DIR)
    try:
        names = sorted(os.listdir(base))
    except OSError:
        return []
    return [
        os.path.join(base, name)
        for name in names
        if name.startswith(AGENT_PREFIX)
        and os.path.isdir(os.path.join(base, name))
        and not os.path.islink(os.path.join(base, name))
    ]


def list_worktrees(repo: str, cores: list[str]) -> list[dict]:
    """
    Inventory the linked worktrees of one repository, orphaned agent dirs included.

    Args:
        repo: main worktree root of the repository.
        cores: receives the core dump candidates found while measuring.

    Returns:
        One record per linked worktree git lists and per `.claude/worktrees/agent-*`
        directory it does not list (orphaned), sorted by path.

    Raises:
        GitBaseError: when `git worktree list` fails.
    """
    trees = [tree for tree in _worktrees(repo) if not tree.main]
    listed = {os.path.realpath(tree.path) for tree in trees}
    records = [
        _record(repo, tree.path, tree.branch, tree.head, False, cores) for tree in trees
    ]
    records += [
        _record(repo, path, None, None, True, cores)
        for path in _agent_dirs(repo)
        if os.path.realpath(path) not in listed
    ]
    return sorted(records, key=lambda record: record["path"])
