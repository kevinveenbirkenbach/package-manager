from __future__ import annotations

from typing import List

from pkgmgr.core.git.queries import probe_remote_reachable

from .context import build_context
from .git_remote import ensure_origin_remote, determine_primary_remote_url
from .remote_provision import ensure_remote_repository
from .types import Repository


def _is_git_remote_url(url: str) -> bool:
    # Keep the same filtering semantics as in git_remote.py (duplicated on purpose
    # to keep setup_cmd independent of private helpers).
    u = (url or "").strip()
    if not u:
        return False
    if u.startswith("git@"):
        return True
    if u.startswith("ssh://"):
        return True
    if (u.startswith("https://") or u.startswith("http://")) and u.endswith(".git"):
        return True
    return False


def _setup_local_mirrors_for_repo(
    repo: Repository,
    repositories_base_dir: str,
    all_repos: List[Repository],
    preview: bool,
) -> None:
    ctx = build_context(repo, repositories_base_dir, all_repos)

    print("------------------------------------------------------------")
    print(f"[MIRROR SETUP:LOCAL] {ctx.identifier}")
    print(f"[MIRROR SETUP:LOCAL] dir: {ctx.repo_dir}")
    print("------------------------------------------------------------")

    ensure_origin_remote(repo, ctx, preview)
    print()


def _setup_remote_mirrors_for_repo(
    repo: Repository,
    repositories_base_dir: str,
    all_repos: List[Repository],
    preview: bool,
    ensure_remote: bool,
) -> None:
    ctx = build_context(repo, repositories_base_dir, all_repos)

    print("------------------------------------------------------------")
    print(f"[MIRROR SETUP:REMOTE] {ctx.identifier}")
    print(f"[MIRROR SETUP:REMOTE] dir: {ctx.repo_dir}")
    print("------------------------------------------------------------")

    if ensure_remote:
        ensure_remote_repository(
            repo,
            repositories_base_dir,
            all_repos,
            preview,
        )

    # Probe only git URLs (do not try ls-remote against PyPI etc.)
    # If there are no mirrors at all, probe the primary git URL.
    git_mirrors = {k: v for k, v in ctx.resolved_mirrors.items() if _is_git_remote_url(v)}

    if not git_mirrors:
        primary = determine_primary_remote_url(repo, ctx)
        if not primary or not _is_git_remote_url(primary):
            print("[INFO] No git mirrors to probe.")
            print()
            return

        ok = probe_remote_reachable(primary, cwd=ctx.repo_dir)
        print("[OK]" if ok else "[WARN]", primary)
        print()
        return

    for name, url in git_mirrors.items():
        ok = probe_remote_reachable(url, cwd=ctx.repo_dir)
        print(f"[OK] {name}: {url}" if ok else f"[WARN] {name}: {url}")

    print()


def setup_mirrors(
    selected_repos: List[Repository],
    repositories_base_dir: str,
    all_repos: List[Repository],
    preview: bool = False,
    local: bool = True,
    remote: bool = True,
    ensure_remote: bool = False,
) -> None:
    for repo in selected_repos:
        if local:
            _setup_local_mirrors_for_repo(
                repo,
                repositories_base_dir,
                all_repos,
                preview,
            )

        if remote:
            _setup_remote_mirrors_for_repo(
                repo,
                repositories_base_dir,
                all_repos,
                preview,
                ensure_remote,
            )
