from __future__ import annotations

import os
import stat

from pkgmgr.actions.branch.gc import _describe, _git, _has_submodules
from pkgmgr.core.git.errors import GitBaseError
from pkgmgr.core.git.queries import FILTER_CONFIG, local_config
from pkgmgr.core.git.run import run

REF_NAMESPACES = ("refs/heads", "refs/remotes", "refs/tags")
PEELED = "%(if)%(*objectname)%(then)%(*objectname)%(else)%(objectname)%(end)"
UNMERGED = "unmerged"
DELETED = "deleted"
DIRECTORY = "directory"
SPECIAL = "special"
UNHASHABLE = {
    DIRECTORY: "untracked directory or gitlink",
    SPECIAL: "not a regular file",
}
MAX_REASONS = 5


def _tips(repo: str) -> list[str]:
    out = _git(["for-each-ref", f"--format={PEELED}", *REF_NAMESPACES], repo)
    return sorted(set(out.split()))


def _status_entries(tree: str) -> list[tuple[str, str | None]]:
    raw = _git(
        [
            "status",
            "--porcelain=v2",
            "-z",
            "--untracked-files=all",
            "--no-renames",
        ],
        tree,
    )
    entries: list[tuple[str, str | None]] = []
    for record in raw.split("\0"):
        kind = record[:1]
        if kind == "1":
            parts = record.split(" ", 8)
            entries.append((parts[8], parts[7]))
        elif kind == "u":
            entries.append((record.split(" ", 10)[10], UNMERGED))
        elif kind == "?":
            entries.append((record[2:], None))
    return entries


def _hashes(tree: str, paths: list[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    files: list[str] = []
    for path in paths:
        full = os.path.join(tree, path)
        try:
            mode = os.lstat(full).st_mode
        except FileNotFoundError:
            hashes[path] = DELETED
            continue
        if stat.S_ISREG(mode):
            files.append(path)
        elif stat.S_ISLNK(mode):
            hashes[path] = run(
                ["hash-object", "-t", "blob", "--no-filters", "--stdin"],
                cwd=tree,
                scan=True,
                input_text=os.readlink(full),
            )
        else:
            hashes[path] = DIRECTORY if stat.S_ISDIR(mode) else SPECIAL
    if files:
        out = run(
            ["hash-object", "--no-filters", "--stdin-paths"],
            cwd=tree,
            scan=True,
            input_text="".join(f"{path}\n" for path in files),
        )
        hashes.update(zip(files, out.split("\n")))
    return hashes


def _absent(
    repo: str, tips: list[str], wanted: list[tuple[str, set[str]]]
) -> list[str]:
    query = "".join(f"{tip}:{path}\n" for path, _ in wanted for tip in tips)
    if not query:
        return [path for path, _ in wanted]
    found = run(
        ["cat-file", "--batch-check=%(objectname)"],
        cwd=repo,
        scan=True,
        input_text=query,
    ).split("\n")
    width = len(tips)
    return [
        path
        for index, (path, blobs) in enumerate(wanted)
        if blobs - set(found[index * width : (index + 1) * width])
    ]


def _reachable(repo: str, head: str | None) -> bool:
    if not head:
        return False
    return bool(
        _git(["for-each-ref", "--count=1", f"--contains={head}", *REF_NAMESPACES], repo)
    )


def _unpreserved(
    repo: str, record: dict, tips: list[str]
) -> tuple[int | None, list[str]]:
    tree = record["path"]
    if _has_submodules(tree):
        return None, ["submodules, whose config the scan cannot vet"]
    unsafe = local_config(tree, FILTER_CONFIG)
    if unsafe:
        return None, [f"{', '.join(unsafe)} in the repository config"]
    entries = _status_entries(tree)
    reasons: list[str] = []
    if entries and record["branch"] is None and not _reachable(repo, record["head"]):
        reasons.append("detached HEAD reachable from no ref")
    hashable: list[tuple[str, str | None]] = []
    for path, index_blob in entries:
        if "\n" in path:
            reasons.append(f"{path!r}: path with a newline")
        elif index_blob == UNMERGED:
            reasons.append(f"{path}: unmerged")
        else:
            hashable.append((path, index_blob))
    hashes = _hashes(tree, [path for path, _ in hashable])
    wanted: list[tuple[str, set[str]]] = []
    for path, index_blob in hashable:
        current = hashes[path]
        if current in UNHASHABLE:
            reasons.append(f"{path}: {UNHASHABLE[current]}")
            continue
        blobs = {current} - {DELETED}
        if index_blob and set(index_blob) != {"0"}:
            blobs.add(index_blob)
        if blobs:
            wanted.append((path, blobs))
    reasons += [f"{path}: content in no ref" for path in _absent(repo, tips, wanted)]
    return len(entries), reasons


def preserved(repo: str, records: list[dict]) -> list[dict]:
    """
    Decide for each dirty worktree whether all its work survives its deletion.

    Args:
        repo: main worktree root of the repository.
        records: its worktree records from list_worktrees.

    Returns:
        One entry per dirty or unreadable worktree; `preserved` is true only
        when every changed, staged and untracked file's content is a blob at
        the same path of some branch, remote or tag tip, and a detached HEAD is
        reachable from a ref. `reasons` lists what is not, capped.
    """
    live = [r for r in records if not r["orphaned"] and not r["missing"]]
    tips = _tips(repo) if live else []
    results: list[dict] = []
    for record in live:
        try:
            paths, reasons = _unpreserved(repo, record, tips)
        except (GitBaseError, OSError, UnicodeError) as exc:
            paths, reasons = None, [f"status failed: {_describe(exc)}"]
        if paths == 0:
            continue
        extra = len(reasons) - MAX_REASONS
        results.append(
            {
                "repo": repo,
                "path": record["path"],
                "branch": record["branch"],
                "paths": paths,
                "preserved": not reasons,
                "reasons": reasons[:MAX_REASONS]
                + ([f"... {extra} more"] if extra > 0 else []),
            }
        )
    return results
