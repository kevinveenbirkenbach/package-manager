from __future__ import annotations

import time

from pkgmgr.actions.branch.gc import _describe
from pkgmgr.core.git.errors import GitBaseError

from .balance import balance
from .core_dumps import core_dumps
from .docker_usage import docker_usage
from .preserved import preserved
from .roots import scan_root
from .worktrees import list_worktrees


def disk_report(
    roots: list[str], repo_roots: list[str], threshold_bytes: int, docker: bool
) -> dict:
    """
    Inventory disk usage read-only: it deletes and writes nothing.

    Args:
        roots: directories whose direct children are measured.
        repo_roots: main worktree roots of the repositories whose linked
            worktrees are listed (pkgmgr passes every managed repository).
        threshold_bytes: list only root children larger than this.
        docker: also read `docker system df`.

    Returns:
        A JSON-serialisable dict. Sizes are allocated bytes (st_blocks * 512,
        sparse files and hard links counted as stored), measured without
        following symlinks or leaving the filesystem a walk starts on; times
        are epoch seconds.
            generated_at: when the scan started.
            threshold_bytes: as given.
            worktrees: per linked worktree and orphaned `.claude/worktrees/agent-*`
                dir: repo, path, branch, head, orphaned, missing, size_bytes,
                last_activity (newest mtime inside or of its index/HEAD),
                foreign_entries (not owned by the current uid, pruned at the first
                per subtree), unreadable (directories that could not be listed).
            preserved: per dirty worktree: repo, path, branch, paths (changed,
                staged and untracked; None when status was not read), preserved,
                reasons.
            roots: per root: root, children over the threshold with path, kind
                (worktree, git-repo, venv, node_modules, cache, core-dump, dir,
                file), size_bytes, newest_mtime, unreadable; biggest first.
            core_dumps: files named `core` or `core.<digits>` under the roots and
                worktrees whose ELF e_type is ET_CORE: path, size_bytes,
                apparent_bytes (st_size), mtime; biggest first.
            docker: rows of type, total, active, size, reclaimable; None when not
                asked for or unavailable.
            balance: per filesystem of the roots and repository roots: filesystem
                (mount point), total_bytes, free_bytes, attributed_bytes.
            warnings: what could not be read.
    """
    started = time.time()
    warnings: list[str] = []
    cores: list[str] = []
    trees: list[dict] = []
    kept: list[dict] = []
    for repo in repo_roots:
        try:
            records = list_worktrees(repo, cores)
        except (GitBaseError, OSError) as exc:
            warnings.append(f"{repo}: worktrees not listed: {_describe(exc)}")
            continue
        trees += records
        try:
            kept += preserved(repo, records)
        except (GitBaseError, OSError) as exc:
            warnings.append(f"{repo}: preservation not checked: {_describe(exc)}")
    scanned: list[dict] = []
    for root in roots:
        try:
            scanned.append(scan_root(root, threshold_bytes, cores))
        except OSError as exc:
            warnings.append(f"{root}: not scanned: {_describe(exc)}")
    dumps = core_dumps(cores)
    usage = None
    if docker:
        usage, warning = docker_usage()
        if warning:
            warnings.append(warning)
    items = [(t["path"], t["size_bytes"]) for t in trees if t["size_bytes"]]
    items += [(c["path"], c["size_bytes"]) for s in scanned for c in s["children"]]
    items += [(d["path"], d["size_bytes"]) for d in dumps]
    return {
        "generated_at": started,
        "threshold_bytes": threshold_bytes,
        "worktrees": trees,
        "preserved": kept,
        "roots": scanned,
        "core_dumps": dumps,
        "docker": usage,
        "balance": balance([*roots, *repo_roots], items),
        "warnings": warnings,
    }
