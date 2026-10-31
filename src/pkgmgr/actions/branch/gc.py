from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, field

from pkgmgr.core.git.commands import delete_local_branch
from pkgmgr.core.git.errors import GitRunError
from pkgmgr.core.git.queries import list_remotes, resolve_base_branch
from pkgmgr.core.git.run import run

from .gc_forge import ForgeFacts, fetch_forge_facts

# PROC_PID_INIT_INO: only the initial PID namespace sees every process of the host.
INIT_PID_NAMESPACE = "pid:[4026531836]"
CLEANUP_IMAGE = "alpine:3.20"
COMPOSE_PROJECT = "com.docker.compose.project"
COMPOSE_WORKING_DIR = "com.docker.compose.project.working_dir"
LOCK_PID = re.compile(r"\bpid (\d+)")
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
    local_sha: str | None = None
    remotes: dict[str, str] = field(default_factory=dict)
    compose_projects: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    state: str = ""
    merged_by: str | None = None
    skip: str | None = None
    actions: list[str] = field(default_factory=list)
    reason: str = ""
    result: str | None = None

    @property
    def eligible(self) -> bool:
        return self.state == "merged-clean" and self.skip is None and bool(self.actions)

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
    forge: ForgeFacts
    containers: list[Container] | None
    host_ns: bool
    warnings: list[str] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)


def host_pid_namespace() -> bool:
    try:
        return os.readlink("/proc/self/ns/pid") == INIT_PID_NAMESPACE
    except OSError:
        return False


def main_repo_root(cwd: str) -> str:
    return os.path.dirname(_common_dir(cwd))


def _common_dir(cwd: str) -> str:
    return run(["rev-parse", "--path-format=absolute", "--git-common-dir"], cwd=cwd)


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


def _worktrees(repo_root: str) -> list[Worktree]:
    trees: list[Worktree] = []
    for block in run(["worktree", "list", "--porcelain"], cwd=repo_root).split("\n\n"):
        fields: dict[str, str] = {}
        for line in block.splitlines():
            key, _, value = line.partition(" ")
            fields[key] = value
        if "worktree" not in fields:
            continue
        branch = fields.get("branch")
        trees.append(
            Worktree(
                path=fields["worktree"],
                head=fields.get("HEAD"),
                branch=branch.removeprefix("refs/heads/") if branch else None,
                locked=fields.get("locked"),
                prunable="prunable" in fields,
                main=not trees,
            )
        )
    return trees


def _refs(
    repo_root: str, remotes: list[str]
) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    out = run(
        [
            "for-each-ref",
            "--format=%(refname) %(objectname)",
            "refs/heads",
            "refs/remotes",
        ],
        cwd=repo_root,
    )
    by_length = sorted(remotes, key=len, reverse=True)
    local: dict[str, str] = {}
    remote: dict[str, dict[str, str]] = {}
    for line in out.splitlines():
        ref, sha = line.split(" ")
        if ref.startswith("refs/heads/"):
            local[ref.removeprefix("refs/heads/")] = sha
            continue
        rest = ref.removeprefix("refs/remotes/")
        owner = next((r for r in by_length if rest.startswith(r + "/")), None)
        if owner and rest[len(owner) + 1 :] != "HEAD":
            remote.setdefault(rest[len(owner) + 1 :], {})[owner] = sha
    return local, remote


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
        run(["merge-base", "--is-ancestor", sha, ref], cwd=repo_root)
    except GitRunError as exc:
        if exc.returncode == 1:
            return False
        raise
    return True


def _merged_by(repo: Repo, sha: str) -> str | None:
    if sha not in repo.first_parent and _is_ancestor(sha, repo.default, repo.repo):
        return "ancestor"
    number = repo.forge.merged_heads.get(sha)
    return f"pr#{number}" if number else None


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
    lock = _lock_skip(tree.locked, repo.host_ns)
    if lock:
        return lock
    busy = sorted(pid for pid, cwd in cwds.items() if _inside(cwd, tree.path))
    if busy:
        return f"process: pid {busy[0]} ({_comm(busy[0])})"
    return None


def _build(
    repo: Repo,
    branch: str | None,
    tree: Worktree | None,
    snapshot: tuple[dict[str, str], dict[str, dict[str, str]], dict[int, str]],
) -> Item:
    local, remote, cwds = snapshot
    item = Item(
        branch=branch,
        worktree=tree.path if tree else None,
        local_sha=local.get(branch) if branch else None,
        remotes=dict(remote.get(branch, {})) if branch else {},
    )
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
    checkout = tree is not None and not tree.prunable and os.path.isdir(tree.path)

    try:
        dirty = (
            len(
                run(
                    ["status", "--porcelain", "--untracked-files=all"], cwd=tree.path
                ).splitlines()
            )
            if checkout and not tree.main
            else 0
        )
    except GitRunError as exc:
        item.state, item.reason = "dirty", f"status failed: {_describe(exc)}"
        dirty = -1

    if dirty > 0:
        item.state, item.reason = "dirty", f"dirty: {dirty} paths"
    elif dirty == 0 and unmerged:
        ahead = int(
            run(
                ["rev-list", "--count", f"{repo.default}..{unmerged[0]}"], cwd=repo.repo
            )
        )
        item.state = "unmerged"
        item.reason = (
            f"unmerged: {ahead} commits not in {repo.default}"
            if ahead
            else "no own commits"
        )
    elif dirty == 0:
        item.state = "merged-clean"
        item.merged_by = next(
            (verdict for verdict in verdicts.values() if verdict != "ancestor"),
            "ancestor",
        )
        item.reason = f"merged by {item.merged_by}"

    item.skip = _skip(repo, item, tree, checkout, cwds)
    for project in item.compose_projects:
        item.actions += [f"compose-down:{project}", f"images:{project}"]
    if tree:
        item.actions.append("worktree")
    if item.local_sha:
        item.actions.append("local-branch")
    item.actions += [f"remote-branch:{name}" for name in item.remotes]
    return item


def _snapshot(
    repo: Repo,
) -> tuple[
    list[Worktree], tuple[dict[str, str], dict[str, dict[str, str]], dict[int, str]]
]:
    local, remote = _refs(repo.repo, repo.remotes)
    cwds = _process_cwds() if repo.host_ns else {}
    return _worktrees(repo.repo), (local, remote, cwds)


def _items(repo: Repo) -> list[Item]:
    trees, snapshot = _snapshot(repo)
    local, remote, _ = snapshot
    by_branch = {t.branch: t for t in trees if t.branch}
    names = sorted(set(local) | set(remote) | set(by_branch))
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


def plan_repo(
    repo_root: str, containers: list[Container] | None, host_ns: bool
) -> Repo:
    warnings: list[str] = []
    try:
        # Auto-maintenance runs worktree-prune, which deletes the metadata of
        # sandboxed worktrees whose gitdir stub is missing.
        run(
            ["fetch", "--all", "--prune", "--quiet", "--no-auto-maintenance"],
            cwd=repo_root,
        )
    except GitRunError as exc:
        warnings.append(f"fetch failed: {_describe(exc)}")
    if containers is None:
        warnings.append("docker unavailable: worktree items are skipped")

    remotes = sorted(list_remotes(cwd=repo_root), key=lambda r: (r != "origin", r))
    heads: dict[str, str] = {}
    for remote in remotes:
        try:
            heads[remote] = run(
                ["symbolic-ref", "--short", f"refs/remotes/{remote}/HEAD"],
                cwd=repo_root,
            )
        except GitRunError:
            continue
    default = next(iter(heads.values()), None) or resolve_base_branch(
        "main", "master", cwd=repo_root
    )
    head_names = {ref[len(remote) + 1 :] for remote, ref in heads.items()}

    forge = fetch_forge_facts(
        {r: run(["remote", "get-url", r], cwd=repo_root) for r in remotes}
    )
    if forge.unavailable:
        warnings.append(f"forge unavailable: {forge.unavailable}")

    repo = Repo(
        repo=repo_root,
        default=default,
        remotes=remotes,
        protected={default, *ALWAYS_PROTECTED, *head_names, *forge.protected},
        first_parent=set(
            run(["rev-list", "--first-parent", default], cwd=repo_root).splitlines()
        ),
        forge=forge,
        containers=containers,
        host_ns=host_ns,
        warnings=warnings,
    )
    repo.items = _items(repo)
    return repo


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
    with open(os.path.join(path, ".git"), encoding="utf-8") as fh:
        meta = os.path.normpath(
            os.path.join(path, fh.read().strip().removeprefix("gitdir: "))
        )
    if os.path.dirname(meta) != os.path.join(_common_dir(repo_root), "worktrees"):
        raise RuntimeError(f"unexpected worktree metadata path {meta}")

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
        shutil.rmtree(path)
    if os.path.lexists(path):
        raise RuntimeError(f"worktree {path} still exists; metadata {meta} kept")
    shutil.rmtree(meta)


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
    )


def execute(repo: Repo, item: Item) -> None:
    fresh = _rebuild(repo, item)
    if _fingerprint(fresh) != _fingerprint(item):
        item.result = f"skipped: changed since plan ({fresh.skip or fresh.reason})"
        return

    notes: list[str] = []
    try:
        for project in item.compose_projects:
            _docker(["compose", "-p", project, "down", "-v", "--remove-orphans"])
        for image in item.images:
            try:
                _docker(["image", "rm", image])
            except subprocess.CalledProcessError:
                notes.append(f"image kept: {image}")
        if item.worktree:
            _remove_worktree(repo.repo, item.worktree)
        if item.local_sha:
            delete_local_branch(item.branch, cwd=repo.repo, force=True)
        for remote, sha in item.remotes.items():
            run(
                [
                    "push",
                    f"--force-with-lease=refs/heads/{item.branch}:{sha}",
                    remote,
                    f":refs/heads/{item.branch}",
                ],
                cwd=repo.repo,
            )
    except (subprocess.CalledProcessError, RuntimeError, OSError) as exc:
        item.result = f"failed: {_describe(exc)}"
        return
    item.result = "; ".join(["done", *notes])


def _line(item: Item) -> str:
    label = "SKIP" if item.state == "merged-clean" and item.skip else LABELS[item.state]
    parts = [item.reason]
    if item.skip and item.state != "protected":
        parts.append(item.skip)
    if item.worktree and item.state != "stale":
        parts.append(f"worktree {item.worktree}")
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


def _prepare(
    repo_roots: list[str], include: list[str], exclude: list[str]
) -> tuple[list[Repo], bool, Callable[[Item], bool]] | None:
    host_ns = host_pid_namespace()
    containers = list_compose_containers()
    repos = [plan_repo(root, containers, host_ns) for root in repo_roots]
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


def branch_gc(
    repo_roots: list[str],
    *,
    apply: bool,
    as_json: bool,
    include: list[str],
    exclude: list[str],
) -> int:
    """
    Plan, and with apply=True execute, the cleanup of merged and clean branches.

    Args:
        repo_roots: main worktree roots of the repositories to scan.
        apply: execute the plan instead of only printing it.
        as_json: print the plan as JSON instead of text lines.
        include: only items whose branch or worktree path matches one of these.
        exclude: drop items whose branch or worktree path matches one of these.

    Returns:
        0 on success, 1 when an applied item failed, 2 when refused.
    """
    if apply and not host_pid_namespace():
        print(REFUSAL, file=sys.stderr)
        return 2
    prepared = _prepare(repo_roots, include, exclude)
    if prepared is None:
        return 2
    repos, host_ns, chosen = prepared

    if apply:
        for repo in repos:
            for item in repo.items:
                if item.eligible and chosen(item):
                    execute(repo, item)
                    print(
                        f"[gc] {item.branch or item.worktree}: {item.result}",
                        file=sys.stderr,
                    )
    _render(repos, host_ns, chosen, as_json)
    return _finish(repos) if apply else 0


def branch_purge(
    repo_roots: list[str], *, include: list[str], exclude: list[str]
) -> int:
    """
    Delete unmerged or dirty items after a y/N confirmation per item.

    Args:
        repo_roots: main worktree roots of the repositories to scan.
        include: only items whose branch or worktree path matches one of these.
        exclude: drop items whose branch or worktree path matches one of these.

    Returns:
        0 on success, 1 when a confirmed item failed, 2 when refused.
    """
    if not host_pid_namespace():
        print(REFUSAL, file=sys.stderr)
        return 2
    prepared = _prepare(repo_roots, include, exclude)
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
