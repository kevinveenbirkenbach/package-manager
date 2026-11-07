from __future__ import annotations

import fcntl
import json
import os
import re
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone

import yaml

from pkgmgr.core.credentials.store_keys import build_keyring_key
from pkgmgr.core.git.errors import GitBaseError

from . import gc
from .gc_forge import GITHUB_HOST, ForgeFacts, facts_with_token, github_slugs

WORKTREES_ROOT = os.path.join(
    os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"),
    "worktrees",
)
WORKTREE_DEPTH = 6
CACHE_TTL = 600
SLUG = re.compile(r"^(?!\.\.?$)[\w.-]+$")


def now() -> float:
    return time.time()


def _iso(stamp: float) -> str:
    return datetime.fromtimestamp(stamp, timezone.utc).isoformat(timespec="seconds")


def tree_file() -> str:
    state = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return os.environ.get("PKGMGR_TREE_FILE") or os.path.join(
        state, "pkgmgr", "tree", "branch-tree.json"
    )


def _cache_path(owner: str, name: str) -> str:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(base, "pkgmgr", "forge", owner, f"{name}.json")


def secret_service_token() -> tuple[str | None, str | None]:
    """
    Read the GitHub token from the Secret Service without unlocking it.

    Returns:
        (token, None), or (None, why no token is available).
    """
    try:
        import secretstorage
    except ImportError:
        return None, "secretstorage not installed"
    key = build_keyring_key("github", GITHUB_HOST, None)
    try:
        connection = secretstorage.dbus_init()
        try:
            items = list(
                secretstorage.search_items(
                    connection, {"service": key.service, "username": key.username}
                )
            )
            unlocked = [item for item in items if not item.is_locked()]
            if not items:
                return None, "no GitHub token in the Secret Service"
            if not unlocked:
                return None, "Secret Service locked"
            return unlocked[0].get_secret().decode(), None
        finally:
            connection.close()
    except (secretstorage.exceptions.SecretStorageException, OSError) as exc:
        return None, f"Secret Service unavailable: {exc}"


@contextmanager
def _locked(path: str) -> Iterator[None]:
    folder, name = os.path.split(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, f".{name}.lock"), "w", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def _replace(path: str, text: str) -> None:
    folder, name = os.path.split(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(dir=folder, prefix=f".{name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _write(path: str, text: str) -> None:
    with _locked(path):
        _replace(path, text)


def _cached(path: str) -> ForgeFacts | None:
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if now() - data["fetched_at"] >= CACHE_TTL:
            return None
        return ForgeFacts(
            merged_heads=data["merged_heads"],
            open_heads=data["open_heads"],
            protected=set(data["protected"]),
        )
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _store(path: str, facts: ForgeFacts) -> None:
    data = {
        "fetched_at": now(),
        "merged_heads": facts.merged_heads,
        "open_heads": facts.open_heads,
        "protected": sorted(facts.protected),
    }
    _write(path, json.dumps(data))


def _unavailable(reason: str | None) -> tuple[ForgeFacts, str]:
    return ForgeFacts(unavailable=reason), f"unavailable: {reason}"


def forge_facts(
    urls: dict[str, str], token: str | None, reason: str | None
) -> tuple[ForgeFacts, str]:
    """
    Forge facts of one repository from the cache, or live once the cache is stale.

    Args:
        urls: remote name -> URL.
        token: GitHub token from the Secret Service, or None.
        reason: why the token is None.

    Returns:
        The facts and their source: none, cached, live or unavailable: <why>.
    """
    slugs = github_slugs(urls)
    if not slugs:
        return ForgeFacts(), "none"
    invalid = [f"{o}/{n}" for o, n in slugs if not (SLUG.match(o) and SLUG.match(n))]
    if invalid:
        return _unavailable(f"invalid GitHub slug {invalid[0]}")
    merged, label = ForgeFacts(), "cached"
    for owner, name in slugs:
        path = _cache_path(owner, name)
        facts = _cached(path)
        if facts is None:
            if token is None:
                return _unavailable(reason)
            facts = facts_with_token([(owner, name)], token)
            if facts.unavailable:
                return _unavailable(facts.unavailable)
            try:
                _store(path, facts)
                label = "live" if label == "cached" else label
            except OSError as exc:
                label = f"live: cache not written ({exc})"
        merged.merged_heads.update(facts.merged_heads)
        merged.open_heads.update(facts.open_heads)
        merged.protected |= facts.protected
    return merged, label


def _missing(root: str, known: bool, scanned_at: str) -> dict:
    return {
        "path": root,
        "remote": None,
        "default": None,
        "missing": True,
        "known": known,
        "forge": None,
        "scanned_at": scanned_at,
        "warnings": [],
        "items": [],
    }


def _scan(
    root: str,
    known: bool,
    token: str | None,
    reason: str | None,
    containers: list[gc.Container] | None,
    host_ns: bool,
) -> dict:
    scanned_at = _iso(now())
    entry = _missing(root, known, scanned_at)
    if not os.path.exists(os.path.join(root, ".git")):
        return entry
    sources: list[str] = []

    def source(urls: dict[str, str]) -> ForgeFacts:
        facts, label = forge_facts(urls, token, reason)
        sources.append(label)
        return facts

    entry["missing"] = False
    try:
        repo = gc.plan_repo(
            root,
            containers,
            host_ns,
            merged_into=[],
            sizes=False,
            min_age=None,
            scope="all",
            activity=True,
            hooks={},
            fetch=False,
            forge_source=source,
        )
    except GitBaseError as exc:
        entry["warnings"] = [f"scan failed: {str(exc).strip().splitlines()[0]}"]
        return entry
    owner = next((r for r in repo.remotes if repo.default.startswith(f"{r}/")), None)
    entry.update(
        remote=repo.urls[repo.remotes[0]] if repo.remotes else None,
        default=repo.default.removeprefix(f"{owner}/") if owner else repo.default,
        forge=sources[0],
        warnings=repo.warnings,
        items=[asdict(item) for item in repo.items],
    )
    return entry


def _owner_root(checkout: str) -> str | None:
    try:
        with open(os.path.join(checkout, ".git"), encoding="utf-8") as fh:
            gitdir = fh.read().strip().removeprefix("gitdir: ")
    except OSError:
        return None
    parent = os.path.dirname(os.path.realpath(os.path.join(checkout, gitdir)))
    if os.path.basename(parent) != "worktrees":
        return None
    common = os.path.dirname(parent)
    return os.path.dirname(common) if os.path.basename(common) == ".git" else common


def _shared_owners(worktrees_root: str) -> list[str]:
    owners: set[str] = set()
    base = worktrees_root.rstrip("/").count("/")
    for path, dirs, files in os.walk(worktrees_root):
        dirs.sort()
        owner = _owner_root(path) if ".git" in files else None
        if owner:
            owners.add(owner)
        if (
            ".git" in files
            or ".git" in dirs
            or path.count("/") - base >= WORKTREE_DEPTH
        ):
            dirs.clear()
    return sorted(owners)


def branch_tree(
    repo_dirs: list[str], *, fmt: str, output: str | None, worktrees_root: str
) -> int:
    """
    Print or write the branch and worktree state of every repository, without fetching.

    Args:
        repo_dirs: directories of the repositories pkgmgr knows.
        fmt: json or yaml.
        output: file to write atomically; None prints to stdout.
        worktrees_root: shared worktree root whose unknown owners are added.

    Returns:
        0 on success, 1 when the output could not be written.
    """
    known = list(dict.fromkeys(os.path.realpath(d) for d in repo_dirs))
    orphans = [d for d in _shared_owners(worktrees_root) if d not in known]
    token, reason = secret_service_token()
    host_ns = gc.host_pid_namespace()
    containers = gc.list_compose_containers()
    data = {
        "generated_at": _iso(now()),
        "host_pid_namespace": host_ns,
        "delete_ready": token is not None,
        "delete_reason": reason,
        "repos": [
            _scan(root, root in known, token, reason, containers, host_ns)
            for root in known + orphans
        ],
    }
    text = (
        yaml.safe_dump(data, sort_keys=False)
        if fmt == "yaml"
        else json.dumps(data, indent=2) + "\n"
    )
    if output is None:
        sys.stdout.write(text)
        return 0
    try:
        _write(output, text)
    except OSError as exc:
        print(f"Cannot write {output}: {exc}", file=sys.stderr)
        return 1
    return 0


def refresh_tree_entry(repo_root: str) -> None:
    """
    Rescan one repository into the tree file, if the file exists and holds it.

    Args:
        repo_root: main worktree root of the repository.

    Skipped outside the host PID namespace and when the file's entry is newer.
    """
    path = tree_file()
    if not os.path.isfile(path) or not gc.host_pid_namespace():
        return
    root = os.path.realpath(repo_root)
    token, reason = secret_service_token()
    fresh = _scan(root, True, token, reason, gc.list_compose_containers(), True)
    with _locked(path):
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        index = next(
            (i for i, entry in enumerate(data["repos"]) if entry["path"] == root), None
        )
        if index is None or data["repos"][index]["scanned_at"] > fresh["scanned_at"]:
            return
        fresh["known"] = data["repos"][index]["known"]
        data["repos"][index] = fresh
        _replace(path, json.dumps(data, indent=2) + "\n")
