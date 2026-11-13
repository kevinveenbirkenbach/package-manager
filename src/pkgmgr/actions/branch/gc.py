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
from pkgmgr.core.git.errors import GitBaseError, GitRunError
from pkgmgr.core.git.queries import (
    FILTER_CONFIG,
    UNSAFE_CONFIG,
    list_remotes,
    local_config,
    resolve_base_branch,
)
from pkgmgr.core.git.run import (
    CONFIG_VIEWS,
    END_OF_OPTIONS,
    SCAN_FLAGS,
    run,
    strict_env,
)

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
SCOPES = ("worktree", "branch", "all", "purge", "local")
NOT_LINKED = "not a linked worktree of this repository"
NO_REMOTE_DEFAULT = (
    "refused: no remote-tracking default (origin, else the only remote: "
    "refs/remotes/<remote>/HEAD, main or master, resolving inside "
    "refs/remotes/<remote>/), so --local cannot tell which branches are merged"
)
NOT_UTF8 = "refused: git output (ref, remote or path names) is not UTF-8"
DEFAULT_NAMES = ("HEAD", "main", "master")
HELD_FILES = (
    ("rebase-merge/head-name", "rebase in progress"),
    ("rebase-merge/update-refs", "rebase in progress"),
    ("rebase-apply/head-name", "rebase in progress"),
    ("BISECT_START", "bisect in progress"),
)
DELETE_MERGED_KEY = r"^branch\..*\.deletemerged$"
SHARED_STORES = ("refs", "packed-refs", "reftable", "logs", "logs/refs")
WALKED_STORES = ("refs", "reftable", "logs/refs")


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
    refused: str | None = None
    common: str = ""
    opted_out: set[str] = field(default_factory=set)
    upstreams: set[tuple[str, str]] = field(default_factory=set)


def host_pid_namespace() -> bool:
    try:
        return os.readlink("/proc/self/ns/pid") == INIT_PID_NAMESPACE
    except OSError:
        return False


def main_repo_root(cwd: str) -> str:
    return os.path.dirname(_common_dir(cwd))


def local_repo_root(cwd: str) -> str:
    """
    Resolve the main worktree of the repository cwd belongs to, for scope
    `local`.

    Args:
        cwd: a directory inside a checkout, also of a submodule or a
            repository with a separate git dir.

    Returns:
        `git rev-parse --show-toplevel` when cwd is in the main worktree,
        else the first `git worktree list` entry; either way of cwd's own
        repository.

    Raises:
        GitBaseError: when that root's git common dir is not cwd's, when
            cwd's git dir is not its repository's own (see _own_git_dir),
            when either is no repository, or when git output is not UTF-8.
    """
    try:
        with strict_env():
            common, git_dir = _own_git_dir(cwd)
            in_main = git_dir == common
            root = (in_main and _toplevel(cwd)) or _worktrees(cwd)[0].path
            root_common = os.path.realpath(_common_dir(root))
    except UnicodeDecodeError as exc:
        raise GitBaseError(f"{NOT_UTF8} for {cwd!r}") from exc
    except OSError as exc:
        raise GitBaseError(f"{cwd}: {exc}") from exc
    if root_common != common:
        raise GitBaseError(
            f"{cwd}: main worktree {root} belongs to another repository than {common}"
        )
    return root


def _own_git_dir(cwd: str) -> tuple[str, str]:
    """
    Resolve cwd's git common dir and git dir, refusing a foreign git dir.

    Args:
        cwd: a directory inside a checkout or a git dir.

    Returns:
        The realpaths of `git rev-parse --git-common-dir` and
        `--absolute-git-dir`.

    Raises:
        GitBaseError: when the git dir is neither the common dir nor directly
            under `<common>/worktrees/`.
    """
    common = os.path.realpath(_common_dir(cwd))
    git_dir = os.path.realpath(_git(["rev-parse", "--absolute-git-dir"], cwd))
    if git_dir != common and os.path.dirname(git_dir) != os.path.join(
        common, "worktrees"
    ):
        raise GitBaseError(
            f"{cwd}: git dir {git_dir} is neither {common} nor directly under "
            f"{common}/worktrees"
        )
    return common, git_dir


def _toplevel(cwd: str) -> str:
    """
    Read the work tree root of cwd's checkout.

    Args:
        cwd: a directory inside a checkout.

    Returns:
        `git rev-parse --show-toplevel`, or "" in a bare repository.
    """
    try:
        return _git(["rev-parse", "--show-toplevel"], cwd)
    except GitRunError:
        return ""


def _git(args: list[str], cwd: str) -> str:
    return run(args, cwd=cwd, scan=True)


def _config_read(args: list[str], cwd: str, view: str) -> str:
    return run(args, cwd=cwd, scan=True, config_view=view)


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


def _needs_forge(item: Item, tree: Worktree | None) -> bool:
    """
    Whether deciding the item needs the forge's PR and protection facts.

    Args:
        item: the classified item.
        tree: the worktree holding its branch, or None.

    Returns:
        False only for a branch that no worktree holds, without upstream and
        remote branch, merged into the default by ancestry; True otherwise.
    """
    return not (
        tree is None
        and item.merged_by == "ancestor"
        and item.upstream is None
        and not item.remotes
    )


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
    if repo.forge.unavailable and _needs_forge(item, tree):
        return "forge unavailable"
    if tree is None:
        return None
    if tree.main:
        return "checked out in main worktree"
    if repo.scope == "local":
        return f"checked out in worktree {tree.path}"
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
    if repo.scope == "local":
        return _local_actions(repo, item, tree)
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


def _local_actions(repo: Repo, item: Item, tree: Worktree | None) -> list[str]:
    """
    Settle the actions of an item planned with scope `local`.

    Args:
        repo: the planned repository; its default and merged-into lines are
            the refs the branch tip must be an ancestor of.
        item: the classified item; a merged-clean one whose tip is an
            ancestor of none of them gets that as its skip.
        tree: the worktree holding its branch, or None.

    Returns:
        `local-branch` for a merged-clean local branch that no worktree,
        worktree registration, rebase, bisect or symbolic ref holds and whose
        tip is an ancestor of the default or a merged-into line, else
        nothing; never a worktree, stack or remote action.
    """
    if item.state != "merged-clean" or not item.local_sha or tree is not None:
        return []
    held = _held_branches(repo.repo).get(item.branch)
    if held:
        item.skip = item.skip or held
        return []
    targets = [repo.default, *repo.lines]
    if any(_is_ancestor(item.local_sha, ref, repo.repo) for ref in targets):
        return ["local-branch"]
    item.skip = item.skip or (
        f"merged by {item.merged_by}, tip is no ancestor of {', '.join(targets)}"
    )
    return []


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
    names = {
        "worktree": set(by_branch),
        "local": set(local) | set(by_branch),
    }.get(repo.scope, set(local) | set(remote) | set(by_branch))
    items = [
        _build(repo, name, by_branch.get(name), snapshot) for name in sorted(names)
    ]
    if repo.scope == "local":
        return items
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


def _default_remote(remotes: list[str]) -> str | None:
    """
    Pick the one remote whose default scope `local` may measure against.

    Args:
        remotes: the configured remote names.

    Returns:
        origin when configured, else the only remote, else None.
    """
    if "origin" in remotes:
        return "origin"
    return remotes[0] if len(remotes) == 1 else None


def _symbolic(repo_root: str, prefix: str, git_dir: str = "") -> dict[str, str]:
    """
    List the resolvable refs under a prefix with their symref targets.

    Args:
        repo_root: main worktree root of the repository.
        prefix: a ref prefix such as `refs/heads` or `refs/remotes/origin`.
        git_dir: the git common dir (shared refs plus the main worktree's own)
            or a `worktrees/<id>` dir whose refs to list, or "" for the refs
            as repo_root's worktree sees them.

    Returns:
        Full ref name -> the ref it points to, or "" for a plain ref.
    """
    args = ["for-each-ref", "--format=%(refname)%00%(symref)", prefix]
    out = _git([f"--git-dir={git_dir}", *args] if git_dir else args, repo_root)
    return dict(line.split("\x00", 1) for line in out.splitlines())


def _resolve_within(refs: dict[str, str], ref: str) -> str | None:
    """
    Follow a ref's symref chain without leaving a set of refs.

    Args:
        refs: refs under one prefix, as _symbolic lists them.
        ref: the full ref name to resolve.

    Returns:
        The plain ref the chain ends at, or None when a step leaves refs,
        loops or ref is missing.
    """
    seen: set[str] = set()
    while ref in refs and ref not in seen:
        seen.add(ref)
        if not refs[ref]:
            return ref
        ref = refs[ref]
    return None


def _remote_default(repo_root: str, remotes: list[str]) -> str | None:
    """
    Pick the remote-tracking ref that scope `local` measures merges against.

    Args:
        repo_root: main worktree root of the repository.
        remotes: the configured remote names.

    Returns:
        For the remote _default_remote picks, the plain ref its HEAD, else
        main, else master resolves to while every step stays inside
        `refs/remotes/<remote>/`; else None.
    """
    remote = _default_remote(remotes)
    if remote is None:
        return None
    refs = _symbolic(repo_root, f"refs/remotes/{remote}")
    for name in DEFAULT_NAMES:
        target = _resolve_within(refs, f"refs/remotes/{remote}/{name}")
        if target:
            return target
    return None


def _worktree_heads(repo_root: str, git_dirs: list[str]) -> dict[str, str]:
    """
    Read the branch every worktree's HEAD names, on any ref backend.

    Args:
        repo_root: main worktree root of the repository.
        git_dirs: the git common dir first, then each `worktrees/<id>`.

    Returns:
        Branch name -> skip reason, from `git --git-dir=<dir> symbolic-ref
        HEAD` for each of them, whatever its id.

    Raises:
        GitBaseError: when a HEAD is neither readable nor detached.
    """
    heads: dict[str, str] = {}
    for git_dir in git_dirs:
        try:
            target = _git(
                [f"--git-dir={git_dir}", "symbolic-ref", "--quiet", "HEAD"], repo_root
            )
        except GitRunError as exc:
            if exc.returncode == 1:
                continue
            raise
        if target.startswith("refs/heads/"):
            heads.setdefault(
                target.removeprefix("refs/heads/"), f"checked out in {git_dir}"
            )
    return heads


def _git_dirs(repo_root: str) -> list[str]:
    """
    List the git dirs of every worktree of the repository.

    Args:
        repo_root: main worktree root of the repository.

    Returns:
        The git common dir, then each entry of `<common>/worktrees/`, whatever
        its id and whether `git worktree list` shows it.
    """
    common = _common_dir(repo_root)
    base = os.path.join(common, "worktrees")
    entries = sorted(os.listdir(base)) if os.path.isdir(base) else []
    return [common, *(os.path.join(base, entry) for entry in entries)]


def _held_branches(repo_root: str) -> dict[str, str]:
    """
    Find the local branches that something besides a listed worktree holds.

    Args:
        repo_root: main worktree root of the repository.

    Returns:
        Branch name -> skip reason: a symbolic branch, the branch any symbolic
        ref under `refs/` (also a tag or remote-tracking one) or under the
        main worktree's or any registration's `refs/worktree/` names, the HEAD
        of the main repository and of every `worktrees/<id>` registration,
        also one `git worktree list` omits, each rebase-merge and rebase-apply
        head-name, an interactive rebase's update-refs and BISECT_START; all
        read through the git common dir, whichever worktree repo_root is.

    Raises:
        GitBaseError: when git cannot read a registration, symref or HEAD.
        OSError: when a state file exists but cannot be read.
        ValueError: when a state file is not UTF-8.
    """
    git_dirs = _git_dirs(repo_root)
    held: dict[str, str] = {}
    symrefs = _symbolic(repo_root, "refs", git_dirs[0])
    for git_dir in git_dirs[1:]:
        for ref, target in _symbolic(repo_root, "refs/worktree", git_dir).items():
            symrefs[f"worktrees/{os.path.basename(git_dir)}/{ref}"] = target
    for ref, target in symrefs.items():
        if target and ref.startswith("refs/heads/"):
            held.setdefault(
                ref.removeprefix("refs/heads/"), f"symbolic ref to {target}"
            )
        if target.startswith("refs/heads/"):
            held.setdefault(
                target.removeprefix("refs/heads/"), f"target of symbolic ref {ref}"
            )
    for branch, reason in _worktree_heads(repo_root, git_dirs).items():
        held.setdefault(branch, reason)
    for git_dir in git_dirs:
        for name, operation in HELD_FILES:
            try:
                with open(os.path.join(git_dir, name), encoding="utf-8") as fh:
                    lines = fh.read().splitlines()
            except FileNotFoundError:
                continue
            for line in lines:
                ref = line.strip().removeprefix("ref: ")
                if ref.startswith("refs/heads/") or name == "BISECT_START":
                    held.setdefault(
                        ref.removeprefix("refs/heads/"), f"{operation} in {git_dir}"
                    )
    return held


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


def _branch_names(repo_root: str, ref: str, remotes: list[str]) -> set[str]:
    """
    Name the branch a merged-into ref is, whatever form it was given in.

    Args:
        repo_root: main worktree root of the repository.
        ref: the ref as given, e.g. `refs/heads/x`, `x` or `origin/x`.
        remotes: the configured remote names.

    Returns:
        `x` for a ref that resolves to `refs/heads/x` or
        `refs/remotes/<remote>/x`, else nothing.
    """
    out = _git(["rev-parse", "--symbolic-full-name", END_OF_OPTIONS, ref], repo_root)
    full = out.splitlines()[-1] if out else ""
    prefixes = ["refs/heads/", *(f"refs/remotes/{r}/" for r in remotes)]
    return {full.removeprefix(p) for p in prefixes if full.startswith(p)}


def _raise(exc: OSError) -> None:
    raise exc


def _shared_refs(repo_root: str) -> str:
    """
    Detect a ref store that other checkouts share through a symlink.

    Args:
        repo_root: main worktree root of the repository.

    Returns:
        The refusal reason when `refs`, `packed-refs`, `reftable`, `logs` or
        `logs/refs` in the git common dir is a symlink (git-new-workdir), or
        any entry below `refs/`, `reftable/` or `logs/refs/` is, else "".

    Raises:
        OSError: when a directory below them cannot be listed.
    """
    common = _common_dir(repo_root)
    shared = [
        name for name in SHARED_STORES if os.path.islink(os.path.join(common, name))
    ]
    stores = [] if shared else [os.path.join(common, s) for s in WALKED_STORES]
    for store in filter(os.path.isdir, stores):
        for parent, dirs, files in os.walk(store, onerror=_raise):
            shared += [
                os.path.relpath(os.path.join(parent, name), common)
                for name in sorted(dirs + files)
                if os.path.islink(os.path.join(parent, name))
            ]
    if not shared:
        return ""
    return (
        f"refused: {', '.join(shared)} in {common} is a symlink, so checkouts "
        "sharing these refs hold branches git cannot list"
    )


def _refused(
    repo_root: str,
    containers: list[Container] | None,
    host_ns: bool,
    reason: str,
    warnings: list[str],
    *,
    scope: str,
    sizes: bool,
    min_age: float | None,
    activity: bool,
    **_options: object,
) -> Repo:
    """
    Build a repository that scope `local` refuses: no items, nothing deleted.

    Args:
        repo_root: main worktree root of the repository.
        containers: as plan_repo takes them.
        host_ns: as plan_repo takes it.
        reason: why the repository is refused; also appended to warnings.
        warnings: warnings gathered so far.
        scope: the planned scope.
        sizes: as plan_repo takes it.
        min_age: as plan_repo takes it.
        activity: as plan_repo takes it.
        _options: the other plan_repo options, unused.

    Returns:
        The refused repository.
    """
    return Repo(
        repo=repo_root,
        default="",
        remotes=[],
        protected=set(),
        first_parent=set(),
        urls={},
        forge=ForgeFacts(),
        containers=containers,
        host_ns=host_ns,
        lines={},
        sizes=sizes,
        min_age=min_age,
        scope=scope,
        activity=activity,
        hooks={},
        warnings=[*warnings, reason],
        refused=reason,
    )


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
    if scope == "local":
        _own_git_dir(repo_root)
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
    if scope == "local":
        default = _remote_default(repo_root, remotes)
        reason = _shared_refs(repo_root) or (NO_REMOTE_DEFAULT if not default else "")
        if reason:
            return _refused(
                repo_root,
                containers,
                host_ns,
                reason,
                warnings,
                scope=scope,
                sizes=sizes,
                min_age=min_age,
                activity=activity,
            )
    else:
        default = next(iter(heads.values()), None) or resolve_base_branch(
            "main", "master", cwd=repo_root, scan=True
        )
    head_names = {ref[len(remote) + 1 :] for remote, ref in heads.items()}

    urls = {r: _git(["remote", "get-url", "--", r], repo_root) for r in remotes}
    forge = (forge_source or fetch_forge_facts)(urls)
    if forge.unavailable:
        warnings.append(f"forge unavailable: {forge.unavailable}")
    lines, line_names = _lines(repo_root, merged_into, remotes, warnings)
    if scope == "local":
        line_names |= {
            name for ref in lines for name in _branch_names(repo_root, ref, remotes)
        }

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
    if scope == "local":
        repo.opted_out = _opted_out(repo_root)
        repo.upstreams = _local_upstreams(repo_root)
    return repo


def _opted_out(repo_root: str) -> set[str]:
    """
    Find the branches whose `branch.<name>.deleteMerged` is false.

    Args:
        repo_root: main worktree root of the repository.

    Returns:
        Each branch that `git --git-dir=<dir> config` sets false in, for each
        of _git_dirs (so also config.worktree and includeIf onbranch) in each
        of CONFIG_VIEWS, so the union of what the caller's config variables
        and the default system and global config give.

    Raises:
        GitBaseError: when git cannot read one of these configs.
    """
    names: set[str] = set()
    for git_dir in _git_dirs(repo_root):
        for view in CONFIG_VIEWS:
            try:
                out = _config_read(
                    [
                        f"--git-dir={git_dir}",
                        "config",
                        "--null",
                        "--type=bool",
                        "--get-regexp",
                        DELETE_MERGED_KEY,
                    ],
                    repo_root,
                    view,
                )
            except GitRunError as exc:
                if exc.returncode == 1:
                    continue
                raise
            for record in out.split("\0"):
                key, _, value = record.partition("\n")
                if value == "false":
                    names.add(key.removeprefix("branch.").removesuffix(".deletemerged"))
    return names


def _local_upstreams(repo_root: str) -> set[tuple[str, str]]:
    """
    Read each local branch's upstream as git resolves it in any worktree.

    Args:
        repo_root: main worktree root of the repository.

    Returns:
        (branch, upstream branch) for each `%(upstream)` under `refs/heads/`
        that `git --git-dir=<dir> for-each-ref` gives for any of _git_dirs in
        any of CONFIG_VIEWS.
    """
    pairs: set[tuple[str, str]] = set()
    for git_dir in _git_dirs(repo_root):
        for view in CONFIG_VIEWS:
            out = _config_read(
                [
                    f"--git-dir={git_dir}",
                    "for-each-ref",
                    "--format=%(refname)%00%(upstream)",
                    "refs/heads",
                ],
                repo_root,
                view,
            )
            for line in out.splitlines():
                ref, _, upstream = line.partition("\0")
                if upstream.startswith("refs/heads/"):
                    pairs.add(
                        (
                            ref.removeprefix("refs/heads/"),
                            upstream.removeprefix("refs/heads/"),
                        )
                    )
    return pairs


def _keep_by_config(repo: Repo, chosen: Callable[[Item], bool]) -> None:
    """
    Keep, as `git branch --delete-merged` does, each branch whose
    `branch.<name>.deleteMerged` is false and each local upstream of a branch
    that stays, also of one kept so or one the filters leave out.

    Args:
        repo: a repository planned with scope `local`; each kept item that
            would be deleted loses its actions and gets the reason as its skip.
        chosen: the --branch and --exclude filter; only an eligible chosen
            item is deleted, every other branch stays.
    """
    reasons = {
        name: f"kept: branch.{name}.deleteMerged is false" for name in repo.opted_out
    }
    pending = {
        item.branch: item for item in repo.items if item.eligible and chosen(item)
    }
    while True:
        for child, parent in sorted(repo.upstreams):
            if child not in pending:
                reasons.setdefault(parent, f"kept: local upstream of {child}")
        kept = reasons.keys() & pending.keys()
        if not kept:
            return
        for name in kept:
            item = pending.pop(name)
            item.actions = []
            item.skip = item.skip or reasons[name]


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


def _drop_branch_config(repo_root: str, branch: str) -> str | None:
    """
    Remove a deleted branch's `branch.<name>` section, as `branch -D` does,
    from the config file in the repository's own git common dir.

    Args:
        repo_root: main worktree root of the repository.
        branch: the deleted branch; a missing section is no error.

    Returns:
        None, or a note why the section was kept, e.g. a locked config.
    """
    config = os.path.join(_common_dir(repo_root), "config")
    try:
        _git(
            ["config", "--file", config, "--remove-section", f"branch.{branch}"],
            repo_root,
        )
    except GitRunError as exc:
        stderr = (exc.stderr or "").strip()
        if "no such section" in stderr.lower():
            return None
        return f"config branch.{branch} kept: {(stderr or str(exc)).splitlines()[0]}"
    return None


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
        if "local-branch" in item.actions and repo.scope == "local":
            _git(
                [
                    "update-ref",
                    "--no-deref",
                    "-d",
                    f"refs/heads/{item.branch}",
                    item.local_sha,
                ],
                repo.repo,
            )
            note = _drop_branch_config(repo.repo, item.branch)
            notes += [note] if note else []
        elif "local-branch" in item.actions:
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


def _plan(
    root: str, containers: list[Container] | None, host_ns: bool, options: dict
) -> Repo:
    """
    Plan one repository; under scope `local` refuse, instead of raising, one
    that git or the filesystem fails on or whose git output is not UTF-8.

    Args:
        root: main worktree root of the repository.
        containers: as plan_repo takes them.
        host_ns: as plan_repo takes it.
        options: the plan_repo keyword options.

    Returns:
        The planned repository, under scope `local` with its realpath git
        common dir, or the refused one.
    """
    if options["scope"] != "local":
        return plan_repo(root, containers, host_ns, **options)
    try:
        repo = plan_repo(root, containers, host_ns, **options)
        repo.common = os.path.realpath(_common_dir(root))
        return repo
    except UnicodeDecodeError:
        reason = NOT_UTF8
    except (GitBaseError, OSError, ValueError) as exc:
        reason = f"refused: {_describe(exc)}"
    return _refused(root, containers, host_ns, reason, [], **options)


def _gone(repo: Repo) -> str:
    """
    Check that a repository planned with scope `local` is still the one
    planned and that its targets still resolve.

    Args:
        repo: the planned repository.

    Returns:
        Why its remaining items must be skipped, else "".
    """
    try:
        if os.path.realpath(_common_dir(repo.repo)) != repo.common:
            return f"repository {repo.repo} is no longer the planned one"
        gone = [
            ref
            for ref in (repo.default, *repo.lines)
            if _sha(repo.repo, f"{ref}^{{commit}}") is None
        ]
    except (GitBaseError, OSError, ValueError) as exc:
        return f"repository {repo.repo} unreadable: {_describe(exc)}"
    return f"target {', '.join(gone)} is gone" if gone else ""


def _apply(repo: Repo, item: Item) -> None:
    """
    Execute one planned item; under scope `local` without raising.

    Args:
        repo: the planned repository.
        item: an eligible item; under scope `local` it ends with a done,
            failed or skipped result, skipped as _gone tells.
    """
    if repo.scope != "local":
        execute(repo, item)
        return
    gone = _gone(repo)
    if gone:
        item.result = f"skipped: {gone}"
        return
    try:
        execute(repo, item)
    except (RuntimeError, OSError, ValueError) as exc:
        item.result = f"failed: {_describe(exc)}"


def _exit_code(repos: list[Repo], apply: bool) -> int:
    """
    Settle the exit code of a cleanup run.

    Args:
        repos: the planned and, with apply, executed repositories.
        apply: whether the plan was executed.

    Returns:
        1 when an applied item failed, else 2 when a repository was
        refused, else 0.
    """
    if apply and _finish(repos):
        return 1
    return 2 if any(repo.refused for repo in repos) else 0


def prepare(
    repo_roots: list[str],
    include: list[str],
    exclude: list[str],
    options: dict,
) -> tuple[list[Repo], bool, Callable[[Item], bool]] | None:
    host_ns = host_pid_namespace()
    containers = [] if options["scope"] == "local" else list_compose_containers()
    repos = [_plan(root, containers, host_ns, options) for root in repo_roots]
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

    for repo in repos:
        if repo.scope == "local":
            _keep_by_config(repo, chosen)
    return repos, host_ns, chosen


def _finish(repos: list[Repo]) -> int:
    results = [item.result for repo in repos for item in repo.items if item.result]
    if any(result.startswith("done") for result in results) and any(
        repo.containers is not None and repo.scope != "local" for repo in repos
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
            both in one pass; `local` deletes, with `update-ref -d` against
            the planned sha, each local branch that no worktree, rebase or
            bisect holds, that _keep_by_config does not keep and whose tip
            is an ancestor of the remote-tracking
            default or a merged_into line, refuses a repository without such
            a default, and reads no forge token, runs no fetch, push, docker,
            hook or prune.
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
        As _exit_code settles it: 1 when an applied item failed, else 2 when
        refused (also a repository scope `local` refused), else 0.
    """
    if scope not in ("worktree", "branch", "all", "local"):
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
        "fetch": scope != "local",
        "forge_source": (lambda _urls: ForgeFacts()) if scope == "local" else None,
    }
    if scope != "local":
        return _run(repo_roots, options, include, exclude, apply, as_json)
    with strict_env():
        bad = _bad_lines(repo_roots, merged_into)
        if bad:
            print(f"Refusing: {bad}", file=sys.stderr)
            return 2
        return _run(repo_roots, options, include, exclude, apply, as_json)


def _bad_lines(repo_roots: list[str], merged_into: list[str]) -> str:
    """
    Check that every merged-into ref of scope `local` names one branch.

    Args:
        repo_roots: main worktree roots of the repositories to scan; one git
            cannot read is left to the planning, which refuses it.
        merged_into: the refs as given.

    Returns:
        Why a ref is refused, when in some repository it is unknown or
        `rev-parse --symbolic-full-name` does not name exactly one ref under
        `refs/heads/` or `refs/remotes/`, else "".
    """
    for root in repo_roots:
        for ref in merged_into:
            try:
                out = _git(
                    ["rev-parse", "--symbolic-full-name", END_OF_OPTIONS, ref], root
                )
            except GitRunError:
                return f"--merged-into {ref} names no ref in {root}"
            except (GitBaseError, OSError, ValueError):
                break
            names = [line for line in out.splitlines() if line != END_OF_OPTIONS]
            if len(names) != 1 or not names[0].startswith(
                ("refs/heads/", "refs/remotes/")
            ):
                return (
                    f"--merged-into {ref} is not exactly one branch or "
                    f"remote-tracking ref in {root}"
                )
    return ""


def _run(
    repo_roots: list[str],
    options: dict,
    include: list[str],
    exclude: list[str],
    apply: bool,
    as_json: bool,
) -> int:
    """
    Plan, print and with apply execute a cleanup, as cleanup describes it.

    Args:
        repo_roots: main worktree roots of the repositories to scan.
        options: the plan_repo keyword options.
        include: as cleanup takes it.
        exclude: as cleanup takes it.
        apply: as cleanup takes it.
        as_json: as cleanup takes it.

    Returns:
        2 for an unknown include, else as _exit_code settles it.
    """
    prepared = prepare(repo_roots, include, exclude, options)
    if prepared is None:
        return 2
    repos, host_ns, chosen = prepared

    if apply:
        for repo in repos:
            for item in repo.items:
                if item.eligible and chosen(item):
                    _apply(repo, item)
                    print(
                        f"[{options['scope']}] {item.branch or item.worktree}: "
                        f"{item.result}",
                        file=sys.stderr,
                    )
    _render(repos, host_ns, chosen, as_json)
    return _exit_code(repos, apply)


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
