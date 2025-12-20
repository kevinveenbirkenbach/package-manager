from __future__ import annotations

from typing import List

from pkgmgr.core.git.queries import probe_remote_reachable_detail

from .context import build_context
from .git_remote import determine_primary_remote_url, ensure_origin_remote
from .remote_provision import ensure_remote_repository_for_url
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


def _print_probe_result(name: str | None, url: str, *, cwd: str) -> None:
    """
    Print probe result for a git remote URL, including a short failure reason.
    """
    ok, reason = probe_remote_reachable_detail(url, cwd=cwd)

    prefix = f"{name}: " if name else ""
    if ok:
        print(f"[OK] {prefix}{url}")
        return

    print(f"[WARN] {prefix}{url}")
    if reason:
        reason = reason.strip()
        if len(reason) > 240:
            reason = reason[:240].rstrip() + "…"
        print(f"       reason: {reason}")


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

    git_mirrors = {
        k: v for k, v in ctx.resolved_mirrors.items() if _is_git_remote_url(v)
    }

    # If there are no git mirrors, fall back to primary (git) URL.
    if not git_mirrors:
        primary = determine_primary_remote_url(repo, ctx)
        if not primary or not _is_git_remote_url(primary):
            print("[INFO] No git mirrors to probe or provision.")
            print()
            return

        if ensure_remote:
            print(f"[REMOTE ENSURE] ensuring primary: {primary}")
            ensure_remote_repository_for_url(
                url=primary,
                private_default=bool(repo.get("private", True)),
                description=str(repo.get("description", "")),
                preview=preview,
            )
            print()

        _print_probe_result(None, primary, cwd=ctx.repo_dir)
        print()
        return

    # Provision ALL git mirrors (if requested)
    if ensure_remote:
        for name, url in git_mirrors.items():
            print(f"[REMOTE ENSURE] ensuring mirror {name!r}: {url}")
            ensure_remote_repository_for_url(
                url=url,
                private_default=bool(repo.get("private", True)),
                description=str(repo.get("description", "")),
                preview=preview,
            )
        print()

    # Probe ALL git mirrors
    for name, url in git_mirrors.items():
        _print_probe_result(name, url, cwd=ctx.repo_dir)

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
