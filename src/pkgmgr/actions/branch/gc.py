from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field

from pkgmgr.actions.worktree.hooks import FINI_HOOK, hook_command, run_hook
from pkgmgr.core.git.errors import GitRunError
from pkgmgr.core.git.queries import (
    FILTER_CONFIG,
    UNSAFE_CONFIG,
    list_remotes,
    local_config,
    resolve_base_branch,
)
from pkgmgr.core.git.run import END_OF_OPTIONS, SCAN_FLAGS, run

from .gc_forge import ForgeFacts, fetch_forge_facts
from .nofollow import canonical, remove_tree

Registrations = tuple[str, dict[str, list[str]]]
Snapshot = tuple[
    dict[str, str],
    dict[str, dict[str, str]],
    dict[int, str],
    dict[str, tuple[str | None, int | None, int | None, bool]],
    Registrations,
]

# PROC_PID_INIT_INO: only the initial PID namespace sees every process of the host.
INIT_PID_NAMESPACE = "pid:[4026531836]"
CLEANUP_IMAGE = "alpine:3.20"
COMPOSE_PROJECT = "com.docker.compose.project"
COMPOSE_WORKING_DIR = "com.docker.compose.project.working_dir"
LOCK_PID = re.compile(r"\bpid (\d+)")
TRACK = re.compile(r"(ahead|behind) (\d+)")
GITLINK = "160000"
STATUS_PATH_FIELD = {"1": 8, "2": 9, "u": 10, "?": 1}
ALWAYS_PROTECTED = ("main", "master")
LABELS = {
    "merged-clean": "DELETE",
    "unmerged": "KEEP",
    "dirty": "KEEP",
    "protected": "PROTECT",
    "stale": "STALE",
}
REFUSAL = (
    "Refusing: not in the host PID namespace (e.g. a sandbox), so running "
    "processes and worktree locks cannot be verified. Run it on the host."
)
SCOPES = ("worktree", "branch", "all", "purge")
NOT_LINKED = "not a linked worktree of this repository"


@dataclass
class Worktree:
    path: str
    head: str | None
    branch: str | None
    locked: str | None
    prunable: bool
    main: bool


@dataclass
class Container:
    project: str
    working_dir: str
    image: str


@dataclass
class Item:
    branch: str | None
    worktree: str | None = None
    head: str | None = None
    detached: bool = False
    locked: str | None = None
    worktree_state: str | None = None
    staged: int | None = None
    unstaged: int | None = None
    untracked: int | None = None
    upstream: str | None = None
    ahead: int | None = None
    behind: int | None = None
    gone: bool = False
    local_sha: str | None = None
    remotes: dict[str, str] = field(default_factory=dict)
    compose_projects: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    state: str = ""
    merged: bool = False
    dirty: int = 0
    merged_by: str | None = None
    merged_into: str | None = None
    unpushed: int | None = None
    last_activity: int | None = None
    size_bytes: int | None = None
    skip: str | None = None
    actions: list[str] = field(default_factory=list)
    reason: str = ""
    result: str | None = None

    @property
    def eligible(self) -> bool:
        return self.skip is None and bool(self.actions)

    def matches(self, name: str) -> bool:
        return name == self.branch or (
            self.worktree is not None and os.path.abspath(name) == self.worktree
        )


@dataclass
class Repo:
    repo: str
    default: str
    remotes: list[str]
    protected: set[str]
    first_parent: set[str]
    urls: dict[str, str]
    forge: ForgeFacts
    containers: list[Container] | None
    host_ns: bool
    lines: dict[str, tuple[str, set[str]]]
    sizes: bool
    min_age: float | None
    scope: str
    activity: bool
    hooks: dict[str, list[str]]
    warnings: list[str] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)
    unsafe: list[str] = field(default_factory=list)


def host_pid_namespace() -> bool:
    try:
        return os.readlink("/proc/self/ns/pid") == INIT_PID_NAMESPACE
    except OSError:
        return False


def main_repo_root(cwd: str) -> str:
    return os.path.dirname(_common_dir(cwd))


def _git(args: list[str], cwd: str) -> str:
    return run(args, cwd=cwd, scan=True)


def _common_dir(cwd: str) -> str:
    return _git(["rev-parse", "--path-format=absolute", "--git-common-dir"], cwd)


def _docker(args: list[str]) -> str:
    return subprocess.run(
        ["docker", *args], check=True, capture_output=True, text=True
    ).stdout


def _describe(exc: Exception) -> str:
    if isinstance(exc, subprocess.CalledProcessError):
        return f"{' '.join(exc.cmd)}: {(exc.stderr or '').strip()}"
    return str(exc).strip().splitlines()[0]


def list_compose_containers() -> list[Container] | None:
    fmt = (
        f'{{{{.Label "{COMPOSE_PROJECT}"}}}}\t'
        f'{{{{.Label "{COMPOSE_WORKING_DIR}"}}}}\t{{{{.Image}}}}'
    )
    try:
        out = _docker(
            ["ps", "-a", "--filter", f"label={COMPOSE_WORKING_DIR}", "--format", fmt]
        )
    except FileNotFoundError:
        return []
    except subprocess.CalledProcessError:
        return None
    return [
        Container(*line.split("\t"))
        for line in out.splitlines()
        if line.count("\t") == 2
    ]


def _inside(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip("/") + "/")


def _registrations(repo_root: str) -> Registrations:
    base = os.path.join(_common_dir(repo_root), "worktrees")
    claims: dict[str, list[str]] = {}
    for entry in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        entry_dir = os.path.join(base, entry)
        target = _pointer(os.path.join(entry_dir, "gitdir"), entry_dir)
        if target:
            claims.setdefault(target, []).append(entry)
    return base, claims


def _linked_meta(registrations: Registrations, path: str) -> str | None:
    """
    Resolve a worktree's metadata directory through its `.git` file.

    Args:
        registrations: `<common>/worktrees` and, per gitdir target, the
            registrations naming it, from _registrations.
        path: worktree path as `git worktree list` derives it from the
            writable `<common>/worktrees/<id>/gitdir`, so possibly forged.

    Returns:
        `<common>/worktrees/<id>` when path, the registration and
        `<common>/worktrees` are canonical, path's `.git` resolves to that
        registration and it is the only registration whose gitdir names
        `<path>/.git`, else None.
    """
    base, claims = registrations
    if not (canonical(path) and canonical(base)):
        return None
    git_file = os.path.join(path, ".git")
    meta = _pointer(git_file, path)
    if meta is None or os.path.dirname(meta) != base or not canonical(meta):
        return None
    return meta if claims.get(git_file) == [os.path.basename(meta)] else None


def _pointer(file: str, relative_to: str) -> str | None:
    if not os.path.isfile(file):
        return None
    try:
        with open(file, encoding="utf-8") as fh:
            target = fh.read().strip().removeprefix("gitdir: ")
    except (OSError, ValueError):
        return None
    return os.path.normpath(os.path.join(relative_to, target))


def _worktrees(repo_root: str) -> list[Worktree]:
    trees: list[Worktree] = []
    fields: dict[str, str] = {}
    for part in _git(["worktree", "list", "--porcelain", "-z"], repo_root).split("\0"):
        if part:
            key, _, value = part.partition(" ")
            fields[key] = value
            continue
        record, fields = fields, {}
        if "worktree" not in record:
            continue
        branch = record.get("branch")
        trees.append(
            Worktree(
                path=record["worktree"],
                head=record.get("HEAD"),
                branch=branch.removeprefix("refs/heads/") if branch else None,
                locked=record.get("locked"),
                prunable="prunable" in record,
                main=not trees,
            )
        )
    return trees


def _tracking(
    upstream: str, track: str
) -> tuple[str | None, int | None, int | None, bool]:
    if not upstream:
        return None, None, None, False
    if track == "gone":
        return upstream, None, None, True
    counts = dict(TRACK.findall(track))
    return upstream, int(counts.get("ahead", 0)), int(counts.get("behind", 0)), False


def _refs(
    repo_root: str, remotes: list[str]
) -> tuple[
    dict[str, str],
    dict[str, dict[str, str]],
    dict[str, tuple[str | None, int | None, int | None, bool]],
]:
    out = _git(
        [
            "for-each-ref",
            "--format=%(refname)%00%(objectname)%00%(upstream:short)%00%(upstream:track,nobracket)",
            "refs/heads",
            "refs/remotes",
        ],
        repo_root,
    )
    by_length = sorted(remotes, key=len, reverse=True)
    local: dict[str, str] = {}
    remote: dict[str, dict[str, str]] = {}
    tracking: dict[str, tuple[str | None, int | None, int | None, bool]] = {}
    for line in out.splitlines():
        ref, sha, upstream, track = line.split("\x00")
        if ref.startswith("refs/heads/"):
            local[ref.removeprefix("refs/heads/")] = sha
            tracking[ref.removeprefix("refs/heads/")] = _tracking(upstream, track)
            continue
        rest = ref.removeprefix("refs/remotes/")
        owner = next((r for r in by_length if rest.startswith(r + "/")), None)
        if owner and rest[len(owner) + 1 :] != "HEAD":
            remote.setdefault(rest[len(owner) + 1 :], {})[owner] = sha
    return local, remote, tracking


def _process_cwds() -> dict[int, str]:
    cwds: dict[int, str] = {}
    for entry in os.listdir("/proc"):
        if entry.isdigit() and int(entry) != os.getpid():
            try:
                cwds[int(entry)] = os.readlink(f"/proc/{entry}/cwd")
            except OSError:
                continue
    return cwds


def _comm(pid: int) -> str:
    try:
        with open(f"/proc/{pid}/comm", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "?"


def _lock_skip(reason: str | None, host_ns: bool) -> str | None:
    if reason is None:
        return None
    match = LOCK_PID.search(reason)
    if not match:
        return f"lock: {reason or 'without reason'}"
    if not host_ns:
        return "lock: liveness unknown"
    pid = int(match.group(1))
    return f"lock: pid {pid} alive" if os.path.exists(f"/proc/{pid}") else None


def _is_ancestor(sha: str, ref: str, repo_root: str) -> bool:
    try:
        _git(["merge-base", "--is-ancestor", END_OF_OPTIONS, sha, ref], repo_root)
    except GitRunError as exc:
        if exc.returncode == 1:
            return False
        raise
    return True


def _in_line(repo: Repo, sha: str) -> str | None:
    for line, (tip, first_parent) in repo.lines.items():
        if sha == tip:
            continue
        if sha in first_parent or _is_ancestor(sha, line, repo.repo):
            return line
    return None


def _merged_by(repo: Repo, sha: str) -> str | None:
    if sha not in repo.first_parent and _is_ancestor(sha, repo.default, repo.repo):
        return "ancestor"
    number = repo.forge.merged_heads.get(sha)
    if number:
        return f"pr#{number}"
    line = _in_line(repo, sha)
    if line:
        return f"line:{line}"
    return "patch" if _patch_merged(repo, sha) else None


def _patch_merged(repo: Repo, sha: str) -> bool:
    cherry = _git(["cherry", END_OF_OPTIONS, repo.default, sha], repo.repo).splitlines()
    if not cherry or any(not line.startswith("- ") for line in cherry):
        return False
    outside = set(
        _git(["rev-list", END_OF_OPTIONS, f"{repo.default}..{sha}"], repo.repo).split()
    )
    return outside == {line[2:] for line in cherry}


def _du_bytes(path: str) -> int | None:
    out = subprocess.run(
        ["du", "-sk", "--", path], check=False, capture_output=True, text=True
    ).stdout.split()
    return int(out[0]) * 1024 if out and out[0].isdigit() else None


def _last_activity(
    repo: Repo, shas: list[str], tree: Worktree | None, changed: list[str]
) -> int:
    stamps = [int(_git(["log", "-1", "--format=%ct", sha], repo.repo)) for sha in shas]
    if tree and os.path.isfile(os.path.join(tree.path, ".git")):
        with open(os.path.join(tree.path, ".git"), encoding="utf-8") as fh:
            index = os.path.join(fh.read().strip().removeprefix("gitdir: "), "index")
        if os.path.isfile(index):
            stamps.append(int(os.path.getmtime(index)))
        for path in changed:
            try:
                stamps.append(int(os.lstat(os.path.join(tree.path, path)).st_mtime))
            except OSError:
                continue
    return max(stamps)


def human_size(size: int) -> str:
    value = float(size)
    for unit in ("K", "M", "G"):
        value /= 1024
        if value < 1024:
            return f"{value:.1f}{unit}"
    return f"{value / 1024:.1f}T"


def _skip(
    repo: Repo,
    item: Item,
    tree: Worktree | None,
    checkout: bool,
    cwds: dict[int, str],
) -> str | None:
    number = repo.forge.open_heads.get(item.branch) if item.branch else None
    if number:
        return f"open-pr #{number}"
    if repo.forge.unavailable:
        return "forge unavailable"
    if tree is None:
        return None
    if tree.main:
        return "checked out in main worktree"
    if not checkout:
        return "worktree checkout missing"
    if repo.containers is None:
        return "docker unavailable"
    shared = sorted(
        {
            c.project
            for c in repo.containers
            if c.project in item.compose_projects
            and not _inside(c.working_dir, tree.path)
        }
    )
    if shared:
        return (
            f"compose project {', '.join(shared)} also has containers "
            "outside the worktree"
        )
    lock = _lock_skip(tree.locked, repo.host_ns)
    if lock:
        return lock
    return _busy(cwds, tree.path)


def _remote_refusal(unsafe: list[str], item: Item) -> str | None:
    if unsafe and any(a.startswith("remote-branch:") for a in item.actions):
        return f"repository config sets {', '.join(unsafe)}"
    return None


def _busy(cwds: dict[int, str], path: str) -> str | None:
    busy = sorted(pid for pid, cwd in cwds.items() if _inside(cwd, path))
    return f"process: pid {busy[0]} ({_comm(busy[0])})" if busy else None


def _has_submodules(path: str) -> bool:
    return any(
        line.startswith(f"{GITLINK} ")
        for line in _git(["ls-files", "--stage"], path).splitlines()
    )


def _status(path: str) -> tuple[list[str], int, int, int]:
    records: list[str] = []
    paths: list[str] = []
    fields = iter(
        _git(["status", "--porcelain=v2", "-z", "--untracked-files=all"], path).split(
            "\0"
        )
    )
    for record in fields:
        kind = record[:1]
        if kind not in STATUS_PATH_FIELD:
            continue
        records.append(record)
        paths.append(record.split(" ", STATUS_PATH_FIELD[kind])[-1])
        if kind == "2":
            next(fields, None)
    codes = [record.split(" ", 2)[1] for record in records if record[:1] in "12u"]
    return (
        paths,
        sum(code[0] != "." for code in codes),
        sum(code[1] != "." for code in codes),
        sum(record.startswith("? ") for record in records),
    )


def _read_worktree(item: Item, checkout: bool) -> tuple[int, str | None, list[str]]:
    if item.worktree is None:
        return 0, None, []
    if not checkout:
        item.worktree_state = "missing"
        return 0, None, []
    try:
        if _has_submodules(item.worktree):
            item.worktree_state = "changed"
            return (
                -1,
                "status skipped: submodules, whose config the scan cannot vet",
                [],
            )
        unsafe = local_config(item.worktree, FILTER_CONFIG)
        if unsafe:
            item.worktree_state = "changed"
            return (
                -1,
                f"status skipped: {', '.join(unsafe)} in the repository config",
                [],
            )
        paths, item.staged, item.unstaged, item.untracked = _status(item.worktree)
    except GitRunError as exc:
        item.worktree_state = "changed"
        return -1, f"status failed: {_describe(exc)}", []
    item.worktree_state = "changed" if paths else "clean"
    return len(paths), None, paths


def _build(
    repo: Repo,
    branch: str | None,
    tree: Worktree | None,
    snapshot: Snapshot,
) -> Item:
    local, remote, cwds, tracking, registrations = snapshot
    upstream, ahead, behind, gone = tracking.get(
        branch or "", (None, None, None, False)
    )
    item = Item(
        branch=branch,
        worktree=tree.path if tree else None,
        head=tree.head if tree else None,
        detached=tree is not None and branch is None,
        locked=tree.locked if tree else None,
        upstream=upstream,
        ahead=ahead,
        behind=behind,
        gone=gone,
        local_sha=local.get(branch) if branch else None,
        remotes=dict(remote.get(branch, {})) if branch else {},
    )
    checkout = tree is not None and not tree.prunable and os.path.isdir(tree.path)
    dirty, unread, changed = _read_worktree(item, checkout)
    item.dirty = max(dirty, 0)
    if branch in repo.protected:
        item.state, item.reason = "protected", "default or protected branch"
        return item

    if tree and repo.containers:
        mine = [c for c in repo.containers if _inside(c.working_dir, tree.path)]
        item.compose_projects = sorted({c.project for c in mine})
        item.images = sorted({c.image for c in mine})

    shas = [item.local_sha, *item.remotes.values(), tree.head if tree else None]
    verdicts = {sha: _merged_by(repo, sha) for sha in dict.fromkeys(shas) if sha}
    unmerged = [sha for sha, verdict in verdicts.items() if verdict is None]
    item.merged = bool(verdicts) and not unmerged

    head = tree.head if checkout else item.local_sha
    if unmerged and head:
        tips = {sha for shas in remote.values() for sha in shas.values()}
        item.unpushed = (
            0
            if head in tips
            else int(
                _git(["rev-list", "--count", head, "--not", "--remotes"], repo.repo)
            )
        )

    if unread:
        item.state, item.reason = "dirty", unread
    elif dirty > 0:
        item.state, item.reason = "dirty", f"dirty: {dirty} paths"
    elif unmerged:
        own = int(
            _git(
                [
                    "rev-list",
                    "--count",
                    END_OF_OPTIONS,
                    f"{repo.default}..{unmerged[0]}",
                ],
                repo.repo,
            )
        )
        item.state = "unmerged"
        item.reason = (
            f"unmerged: {own} commits not in {repo.default}"
            if own
            else "no own commits"
        )
    else:
        item.state = "merged-clean"
        item.merged_by = next(
            (verdict for verdict in verdicts.values() if verdict != "ancestor"),
            "ancestor",
        )
        item.merged_into = (
            item.merged_by.removeprefix("line:")
            if item.merged_by.startswith("line:")
            else repo.default
        )
        item.reason = f"merged by {item.merged_by}"

    if repo.sizes and checkout and not tree.main:
        item.size_bytes = _du_bytes(tree.path)
    if verdicts and (repo.activity or repo.min_age is not None):
        item.last_activity = _last_activity(
            repo, list(verdicts), tree if checkout else None, changed
        )
    item.skip = _skip(repo, item, tree, checkout, cwds)
    if (
        item.skip is None
        and repo.min_age is not None
        and item.last_activity
        and (time.time() - item.last_activity) / 3600 < repo.min_age
    ):
        item.skip = f"younger than {repo.min_age:g} h"
    item.actions = _actions(repo, item, tree, checkout, dirty, registrations)
    if repo.unsafe:
        item.actions = [a for a in item.actions if not a.startswith("remote-branch:")]
    return item


def _actions(
    repo: Repo,
    item: Item,
    tree: Worktree | None,
    checkout: bool,
    dirty: int,
    registrations: Registrations,
) -> list[str]:
    tree_part: list[str] = []
    if tree:
        if (
            checkout
            and not tree.main
            and _linked_meta(registrations, tree.path) is None
        ):
            item.skip = NOT_LINKED
            return []
        if checkout and FINI_HOOK in repo.hooks:
            tree_part.append(f"hook:{FINI_HOOK}")
        for project in item.compose_projects:
            tree_part += [f"compose-down:{project}", f"images:{project}"]
        tree_part.append("worktree")
    branch_part = ["local-branch"] if item.local_sha else []
    branch_part += [f"remote-branch:{name}" for name in item.remotes]

    if repo.scope == "purge":
        return tree_part + branch_part
    tree_ok = (
        tree is not None
        and not tree.main
        and dirty == 0
        and (item.merged or item.unpushed == 0)
    )
    branch_ok = item.state == "merged-clean"
    if repo.scope == "worktree":
        return tree_part if tree_ok else []
    if repo.scope == "branch":
        if branch_ok and tree is not None and item.skip is None:
            item.skip = f"checked out in worktree {tree.path}"
        return branch_part if branch_ok and tree is None else []
    actions = tree_part if tree_ok else []
    if branch_ok and (tree is None or tree_ok):
        actions += branch_part
    return actions


def _snapshot(repo: Repo) -> tuple[list[Worktree], Snapshot]:
    local, remote, tracking = _refs(repo.repo, repo.remotes)
    cwds = _process_cwds() if repo.host_ns else {}
    return _worktrees(repo.repo), (
        local,
        remote,
        cwds,
        tracking,
        _registrations(repo.repo),
    )


def _items(repo: Repo) -> list[Item]:
    trees, snapshot = _snapshot(repo)
    local, remote, *_ = snapshot
    by_branch = {t.branch: t for t in trees if t.branch}
    names = (
        sorted(by_branch)
        if repo.scope == "worktree"
        else sorted(set(local) | set(remote) | set(by_branch))
    )
    items = [_build(repo, name, by_branch.get(name), snapshot) for name in names]
    items += [
        _build(repo, None, tree, snapshot)
        for tree in trees
        if tree.branch is None and not tree.main
    ]
    return items + _stale(repo.repo)


def _stale(repo_root: str) -> list[Item]:
    base = os.path.join(_common_dir(repo_root), "worktrees")
    items: list[Item] = []
    for entry in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        meta = os.path.join(base, entry)
        gitdir = os.path.join(meta, "gitdir")
        if not os.path.isfile(gitdir) or os.path.getsize(gitdir) == 0:
            reason = "metadata without gitdir, not pruned"
        else:
            with open(gitdir, encoding="utf-8") as fh:
                target = fh.read().strip()
            if os.path.exists(target):
                continue
            reason = f"checkout {os.path.dirname(target)} missing, not pruned"
        items.append(Item(branch=None, worktree=meta, state="stale", reason=reason))
    return items


def _lines(
    repo_root: str, refs: list[str], remotes: list[str], warnings: list[str]
) -> tuple[dict[str, tuple[str, set[str]]], set[str]]:
    lines: dict[str, tuple[str, set[str]]] = {}
    names: set[str] = set()
    for ref in refs:
        try:
            tip = _git(
                [
                    "rev-parse",
                    "--verify",
                    "--quiet",
                    END_OF_OPTIONS,
                    f"{ref}^{{commit}}",
                ],
                repo_root,
            )
        except GitRunError:
            warnings.append(f"merged-into ref {ref} not found")
            continue
        first_parent = set(
            _git(
                ["rev-list", "--first-parent", END_OF_OPTIONS, ref], repo_root
            ).splitlines()
        )
        lines[ref] = (tip, first_parent)
        owner = next((r for r in remotes if ref.startswith(r + "/")), None)
        names.add(ref[len(owner) + 1 :] if owner else ref)
    return lines, names


def plan_repo(
    repo_root: str,
    containers: list[Container] | None,
    host_ns: bool,
    *,
    merged_into: list[str],
    sizes: bool,
    min_age: float | None,
    scope: str,
    activity: bool,
    hooks: dict[str, dict[str, list[str]]],
    fetch: bool = True,
    forge_source: Callable[[dict[str, str]], ForgeFacts] | None = None,
) -> Repo:
    """
    Scan one repository and classify every branch and worktree.

    Args:
        repo_root: main worktree root of the repository.
        containers: compose containers on the host; None when docker is unavailable.
        host_ns: whether this process runs in the host PID namespace.
        merged_into: integration lines (refs) that also count as merged; each is protected.
        sizes: measure each worktree's disk usage into size_bytes.
        min_age: skip items whose newest commit, worktree index or changed file is younger (hours).
        scope: one of SCOPES; decides which actions an item gets.
        activity: record last_activity on every item, not only under min_age.
        hooks: realpath of a managed repository's root -> hook name -> argv,
            as the CLI binds `worktree_hooks`; only repo_root's entry is used,
            and only while repo_root's git directory is its own.
        fetch: fetch every remote first; the tree scan reads the known refs only.
        forge_source: remote name -> URL to forge facts; fetch_forge_facts by default.

    Returns:
        The repository with its classified items.
    """
    if scope not in SCOPES:
        raise ValueError(f"unknown scope {scope!r}")
    warnings: list[str] = []
    unsafe = local_config(repo_root, UNSAFE_CONFIG)
    if unsafe:
        warnings.append(
            f"fetch and remote branch deletes skipped: the repository config sets "
            f"{', '.join(unsafe)}"
        )
    if fetch and not unsafe:
        try:
            # Auto-maintenance runs worktree-prune, which deletes the metadata of
            # sandboxed worktrees whose gitdir stub is missing.
            run(
                [
                    *SCAN_FLAGS,
                    "fetch",
                    "--all",
                    "--prune",
                    "--quiet",
                    "--no-auto-maintenance",
                    "--no-recurse-submodules",
                ],
                cwd=repo_root,
            )
        except GitRunError as exc:
            warnings.append(f"fetch failed: {_describe(exc)}")
    if containers is None:
        warnings.append("docker unavailable: worktree items are skipped")

    remotes = sorted(
        list_remotes(cwd=repo_root, scan=True), key=lambda r: (r != "origin", r)
    )
    heads: dict[str, str] = {}
    for remote in remotes:
        try:
            heads[remote] = _git(
                ["symbolic-ref", "--short", f"refs/remotes/{remote}/HEAD"], repo_root
            )
        except GitRunError:
            continue
    default = next(iter(heads.values()), None) or resolve_base_branch(
        "main", "master", cwd=repo_root, scan=True
    )
    head_names = {ref[len(remote) + 1 :] for remote, ref in heads.items()}

    urls = {r: _git(["remote", "get-url", "--", r], repo_root) for r in remotes}
    forge = (forge_source or fetch_forge_facts)(urls)
    if forge.unavailable:
        warnings.append(f"forge unavailable: {forge.unavailable}")
    lines, line_names = _lines(repo_root, merged_into, remotes, warnings)

    repo = Repo(
        repo=repo_root,
        default=default,
        remotes=remotes,
        protected={
            default,
            *ALWAYS_PROTECTED,
            *head_names,
            *forge.protected,
            *line_names,
        },
        first_parent=set(
            _git(
                ["rev-list", "--first-parent", END_OF_OPTIONS, default], repo_root
            ).splitlines()
        ),
        urls=urls,
        forge=forge,
        containers=containers,
        host_ns=host_ns,
        lines=lines,
        sizes=sizes,
        min_age=min_age,
        scope=scope,
        activity=activity,
        hooks=_pins(hooks, repo_root, warnings),
        warnings=warnings,
        unsafe=unsafe,
    )
    repo.items = _items(repo)
    return repo


def _pins(
    hooks: dict[str, dict[str, list[str]]], repo_root: str, warnings: list[str]
) -> dict[str, list[str]]:
    root = os.path.realpath(repo_root)
    pinned = hooks.get(root, {})
    if not pinned:
        return {}
    owner = os.path.realpath(os.path.dirname(_common_dir(repo_root)))
    if owner != root:
        warnings.append(f"pinned hooks skipped: its git directory belongs to {owner}")
        return {}
    return pinned


def _foreign_owned(path: str) -> bool:
    uid = os.getuid()
    if os.lstat(path).st_uid != uid:
        return True
    for root, dirs, files in os.walk(path):
        for name in (*dirs, *files):
            if os.lstat(os.path.join(root, name)).st_uid != uid:
                return True
    return False


def _remove_worktree(repo_root: str, path: str) -> None:
    meta = _linked_meta(_registrations(repo_root), path)
    if meta is None:
        raise RuntimeError(f"{path}: {NOT_LINKED}")

    if _foreign_owned(path):
        parent, name = os.path.split(path.rstrip("/"))
        _docker(
            [
                "run",
                "--rm",
                "-v",
                f"{parent}:/w",
                CLEANUP_IMAGE,
                "rm",
                "-rf",
                f"/w/{name}",
            ]
        )
    else:
        remove_tree(path)
    if os.path.lexists(path):
        raise RuntimeError(f"worktree {path} still exists; metadata {meta} kept")
    remove_tree(meta)


def _rebuild(repo: Repo, item: Item) -> Item:
    trees, snapshot = _snapshot(repo)
    tree = next(
        (
            t
            for t in trees
            if (t.branch == item.branch if item.branch else t.path == item.worktree)
        ),
        None,
    )
    return _build(repo, item.branch, tree, snapshot)


def _fingerprint(item: Item) -> tuple:
    return (
        item.state,
        item.skip,
        item.local_sha,
        item.remotes,
        item.worktree,
        item.compose_projects,
        item.actions,
    )


def _run_fini_hook(repo: Repo, path: str) -> None:
    run_hook(
        FINI_HOOK,
        hook_command(FINI_HOOK, repo.hooks[FINI_HOOK], path, None),
        path,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _sha(cwd: str, ref: str) -> str | None:
    try:
        return _git(["rev-parse", "--verify", "--quiet", END_OF_OPTIONS, ref], cwd)
    except GitRunError:
        return None


def _changed_by_hook(repo: Repo, item: Item) -> str | None:
    path = item.worktree
    dirty, unread, _ = _read_worktree(Item(branch=None, worktree=path), True)
    if unread or dirty:
        return unread or f"dirty: {dirty} paths"
    if _sha(path, "HEAD") != item.head:
        return "HEAD moved"
    if item.branch and _sha(repo.repo, f"refs/heads/{item.branch}") != item.local_sha:
        return f"branch {item.branch} moved"
    return _busy(_process_cwds(), path) if repo.host_ns else None


def execute(repo: Repo, item: Item) -> None:
    fresh = _rebuild(repo, item)
    if _fingerprint(fresh) != _fingerprint(item):
        item.result = f"skipped: changed since plan ({fresh.skip or fresh.reason})"
        return
    refusal = _remote_refusal(local_config(repo.repo, UNSAFE_CONFIG), item)
    if refusal:
        item.result = f"skipped: {refusal}"
        return

    notes: list[str] = []
    removes_tree = "worktree" in item.actions
    if removes_tree and _linked_meta(_registrations(repo.repo), item.worktree) is None:
        item.result = f"skipped: {NOT_LINKED}"
        return
    try:
        if f"hook:{FINI_HOOK}" in item.actions:
            _run_fini_hook(repo, item.worktree)
            changed = _changed_by_hook(repo, item)
            if changed:
                item.result = f"skipped: changed during {FINI_HOOK} ({changed})"
                return
        for project in item.compose_projects if removes_tree else []:
            _docker(["compose", "-p", project, "down", "-v", "--remove-orphans"])
        for image in item.images if removes_tree else []:
            try:
                _docker(["image", "rm", image])
            except subprocess.CalledProcessError:
                notes.append(f"image kept: {image}")
        if removes_tree:
            _remove_worktree(repo.repo, item.worktree)
        if "local-branch" in item.actions:
            _git(["branch", "-D", "--", item.branch], repo.repo)
        for remote, sha in item.remotes.items():
            if f"remote-branch:{remote}" not in item.actions:
                continue
            run(
                [
                    *SCAN_FLAGS,
                    "push",
                    f"--force-with-lease=refs/heads/{item.branch}:{sha}",
                    "--",
                    remote,
                    f":refs/heads/{item.branch}",
                ],
                cwd=repo.repo,
            )
    except (subprocess.CalledProcessError, RuntimeError, OSError) as exc:
        item.result = f"failed: {_describe(exc)}"
        return
    item.result = "; ".join(["done", *notes])


def _label(item: Item) -> str:
    if item.skip and (item.actions or item.state == "merged-clean"):
        return "SKIP"
    if item.actions:
        return "REMOVE" if item.state in ("unmerged", "dirty") else "DELETE"
    return "KEEP" if item.state == "merged-clean" else LABELS[item.state]


def _line(item: Item) -> str:
    label = _label(item)
    parts = [item.reason]
    if item.skip and item.state != "protected":
        parts.append(item.skip)
    if item.worktree and item.state != "stale":
        parts.append(f"worktree {item.worktree}")
    if item.size_bytes is not None:
        parts.append(f"size {human_size(item.size_bytes)}")
    if item.compose_projects:
        parts.append("stack " + ", ".join(item.compose_projects))
    if item.remotes:
        parts.append("remotes " + ", ".join(item.remotes))
    line = f"{label:<8} {item.branch or item.worktree}  {'; '.join(parts)}"
    return f"{line}  -> {item.result}" if item.result else line


def _render(
    repos: list[Repo], host_ns: bool, chosen: Callable[[Item], bool], as_json: bool
) -> None:
    if as_json:
        print(
            json.dumps(
                {
                    "host_pid_namespace": host_ns,
                    "repos": [
                        {
                            "repo": repo.repo,
                            "default": repo.default,
                            "merged_into": list(repo.lines),
                            "warnings": repo.warnings,
                            "items": [asdict(i) for i in repo.items if chosen(i)],
                        }
                        for repo in repos
                    ],
                },
                indent=2,
            )
        )
        return
    for repo in repos:
        print(f"== {repo.repo} (default {repo.default})")
        for warning in repo.warnings:
            print(f"WARN     {warning}")
        for item in repo.items:
            if chosen(item):
                print(_line(item))
    if not host_ns:
        print(
            "WARN     process and lock checks unavailable: "
            "not in the host PID namespace"
        )


def prepare(
    repo_roots: list[str],
    include: list[str],
    exclude: list[str],
    options: dict,
) -> tuple[list[Repo], bool, Callable[[Item], bool]] | None:
    host_ns = host_pid_namespace()
    containers = list_compose_containers()
    repos = [plan_repo(root, containers, host_ns, **options) for root in repo_roots]
    unknown = [
        name
        for name in include
        if not any(item.matches(name) for repo in repos for item in repo.items)
    ]
    if unknown:
        print(f"Unknown --branch: {', '.join(unknown)}", file=sys.stderr)
        return None

    def chosen(item: Item) -> bool:
        return (not include or any(item.matches(n) for n in include)) and not any(
            item.matches(n) for n in exclude
        )

    return repos, host_ns, chosen


def _finish(repos: list[Repo]) -> int:
    results = [item.result for repo in repos for item in repo.items if item.result]
    if any(result.startswith("done") for result in results) and any(
        repo.containers is not None for repo in repos
    ):
        for args in (["image", "prune", "-f"], ["builder", "prune", "-f"]):
            try:
                _docker(args)
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                print(f"WARN     {_describe(exc)}", file=sys.stderr)
    return 1 if any(result.startswith("failed") for result in results) else 0


def cleanup(
    repo_roots: list[str],
    *,
    scope: str,
    apply: bool,
    as_json: bool,
    include: list[str],
    exclude: list[str],
    merged_into: list[str],
    sizes: bool,
    min_age: float | None,
    hooks: dict[str, dict[str, list[str]]],
) -> int:
    """
    Plan, and with apply=True execute, a cleanup of worktrees, branches or both.

    Args:
        repo_roots: main worktree roots of the repositories to scan.
        scope: `worktree` removes clean worktrees whose commits are merged or
            pushed (hook, stack, checkout; the branch stays); `branch` removes
            merged branches without a worktree, local and remote; `all` does
            both in one pass.
        apply: execute the plan instead of only printing it.
        as_json: print the plan as JSON instead of text lines.
        include: only items whose branch or worktree path matches one of these.
        exclude: drop items whose branch or worktree path matches one of these.
        merged_into: integration lines (refs) that also count as merged.
        sizes: measure each worktree's disk usage into the plan.
        min_age: skip items younger than this many hours.
        hooks: pinned hooks by managed repository root realpath, from the
            CLI; a worktree-fini hook runs only for a root pinned there.

    Returns:
        0 on success, 1 when an applied item failed, 2 when refused.
    """
    if scope not in ("worktree", "branch", "all"):
        raise ValueError(f"unknown cleanup scope {scope!r}")
    if apply and not host_pid_namespace():
        print(REFUSAL, file=sys.stderr)
        return 2
    options = {
        "merged_into": merged_into,
        "sizes": sizes,
        "min_age": min_age,
        "scope": scope,
        "activity": False,
        "hooks": hooks,
    }
    prepared = prepare(repo_roots, include, exclude, options)
    if prepared is None:
        return 2
    repos, host_ns, chosen = prepared

    if apply:
        for repo in repos:
            for item in repo.items:
                if item.eligible and chosen(item):
                    execute(repo, item)
                    print(
                        f"[{scope}] {item.branch or item.worktree}: {item.result}",
                        file=sys.stderr,
                    )
    _render(repos, host_ns, chosen, as_json)
    return _finish(repos) if apply else 0


def branch_purge(
    repo_roots: list[str],
    *,
    include: list[str],
    exclude: list[str],
    merged_into: list[str],
    sizes: bool,
    min_age: float | None,
    hooks: dict[str, dict[str, list[str]]],
) -> int:
    """
    Delete unmerged or dirty items after a y/N confirmation per item.

    Args:
        repo_roots: main worktree roots of the repositories to scan.
        include: only items whose branch or worktree path matches one of these.
        exclude: drop items whose branch or worktree path matches one of these.
        merged_into: integration lines (refs) that also count as merged.
        sizes: measure each worktree's disk usage into the prompt line.
        min_age: skip items younger than this many hours.
        hooks: pinned hooks by managed repository root realpath, from the
            CLI; a worktree-fini hook runs only for a root pinned there.

    Returns:
        0 on success, 1 when a confirmed item failed, 2 when refused.
    """
    if not host_pid_namespace():
        print(REFUSAL, file=sys.stderr)
        return 2
    options = {
        "merged_into": merged_into,
        "sizes": sizes,
        "min_age": min_age,
        "scope": "purge",
        "activity": False,
        "hooks": hooks,
    }
    prepared = prepare(repo_roots, include, exclude, options)
    if prepared is None:
        return 2
    repos, _, chosen = prepared

    for repo in repos:
        for item in repo.items:
            if item.state not in ("unmerged", "dirty") or item.skip or not chosen(item):
                continue
            print(_line(item))
            print(f"  removes: {', '.join(item.actions)}")
            try:
                answer = input("Delete this item? This is destructive! (y/N): ")
            except EOFError:
                answer = ""
            if answer.strip().lower() != "y":
                continue
            execute(repo, item)
            print(f"  -> {item.result}")
    return _finish(repos)
