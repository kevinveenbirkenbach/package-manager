# src/pkgmgr/actions/mirror/setup_cmd.py
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

    ensure_origin_remote(repo, ctx, preview=preview)
    print()


def _setup_remote_mirrors_for_repo(
    repo: Repository,
    repositories_base_dir: str,
    all_repos: List[Repository],
    preview: bool,
    ensure_remote: bool,
) -> None:
    ctx = build_context(repo, repositories_base_dir, all_repos)
    resolved_mirrors = ctx.resolved_mirrors

    print("------------------------------------------------------------")
    print(f"[MIRROR SETUP:REMOTE] {ctx.identifier}")
    print(f"[MIRROR SETUP:REMOTE] dir: {ctx.repo_dir}")
    print("------------------------------------------------------------")

    if ensure_remote:
        ensure_remote_repository(
            repo,
            repositories_base_dir=repositories_base_dir,
            all_repos=all_repos,
            preview=preview,
        )

    if not resolved_mirrors:
        primary_url = determine_primary_remote_url(repo, resolved_mirrors)
        if not primary_url:
            print("[INFO] No mirrors configured and no primary URL available.")
            print()
            return

        ok, error_message = probe_mirror(primary_url, ctx.repo_dir)
        if ok:
            print(f"[OK] primary: {primary_url}")
        else:
            print(f"[WARN] primary: {primary_url}")
            for line in error_message.splitlines():
                print(f"         {line}")

        print()
        return

    for name, url in sorted(resolved_mirrors.items()):
        ok, error_message = probe_mirror(url, ctx.repo_dir)
        if ok:
            print(f"[OK] {name}: {url}")
        else:
            print(f"[WARN] {name}: {url}")
            for line in error_message.splitlines():
                print(f"         {line}")

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
                repo=repo,
                repositories_base_dir=repositories_base_dir,
                all_repos=all_repos,
                preview=preview,
            )

        if remote:
            _setup_remote_mirrors_for_repo(
                repo=repo,
                repositories_base_dir=repositories_base_dir,
                all_repos=all_repos,
                preview=preview,
                ensure_remote=ensure_remote,
            )
