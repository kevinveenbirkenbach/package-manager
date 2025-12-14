from __future__ import annotations

from typing import List

from .context import build_context
from .git_remote import ensure_origin_remote, determine_primary_remote_url
from .remote_check import probe_mirror
from .remote_provision import ensure_remote_repository
from .types import Repository


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

    if not ctx.resolved_mirrors:
        primary = determine_primary_remote_url(repo, ctx)
        if not primary:
            return

        ok, msg = probe_mirror(primary, ctx.repo_dir)
        print("[OK]" if ok else "[WARN]", primary)
        if msg:
            print(msg)
        print()
        return

    for name, url in ctx.resolved_mirrors.items():
        ok, msg = probe_mirror(url, ctx.repo_dir)
        print(f"[OK] {name}: {url}" if ok else f"[WARN] {name}: {url}")
        if msg:
            print(msg)

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
