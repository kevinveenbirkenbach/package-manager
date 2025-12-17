from __future__ import annotations

import os
from typing import Optional, Set

from pkgmgr.core.git.errors import GitRunError
from pkgmgr.core.git.commands import (
    GitAddRemoteError,
    GitAddRemotePushUrlError,
    GitSetRemoteUrlError,
    add_remote,
    add_remote_push_url,
    set_remote_url,
)
from pkgmgr.core.git.queries import get_remote_push_urls, list_remotes

from .types import MirrorMap, RepoMirrorContext, Repository


def _is_git_remote_url(url: str) -> bool:
    """
    True only for URLs that should become git remotes / push URLs.

    Accepted:
      - git@host:owner/repo(.git)                (SCP-like SSH)
      - ssh://git@host(:port)/owner/repo(.git)   (SSH URL)
      - https://host/owner/repo.git              (HTTPS git remote)
      - http://host/owner/repo.git               (rare, but possible)
    Everything else (e.g. PyPI project page) stays metadata only.
    """
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


def build_default_ssh_url(repo: Repository) -> Optional[str]:
    provider = repo.get("provider")
    account = repo.get("account")
    name = repo.get("repository")
    port = repo.get("port")

    if not provider or not account or not name:
        return None

    if port:
        return f"ssh://git@{provider}:{port}/{account}/{name}.git"

    return f"git@{provider}:{account}/{name}.git"


def _git_mirrors_only(m: MirrorMap) -> MirrorMap:
    return {k: v for k, v in m.items() if v and _is_git_remote_url(v)}


def determine_primary_remote_url(
    repo: Repository,
    ctx: RepoMirrorContext,
) -> Optional[str]:
    """
    Priority order (GIT URLS ONLY):
      1. origin from resolved mirrors (if it is a git URL)
      2. first git URL from MIRRORS file (in file order)
      3. first git URL from config mirrors (in config order)
      4. default SSH URL
    """
    resolved = ctx.resolved_mirrors
    origin = resolved.get("origin")
    if origin and _is_git_remote_url(origin):
        return origin

    for mirrors in (ctx.file_mirrors, ctx.config_mirrors):
        for _, url in mirrors.items():
            if url and _is_git_remote_url(url):
                return url

    return build_default_ssh_url(repo)


def has_origin_remote(repo_dir: str) -> bool:
    try:
        return "origin" in list_remotes(cwd=repo_dir)
    except GitRunError:
        return False


def _set_origin_fetch_and_push(repo_dir: str, url: str, preview: bool) -> None:
    """
    Ensure origin has fetch URL and push URL set to the primary URL.
    Preview is handled by the underlying git runner.
    """
    set_remote_url("origin", url, cwd=repo_dir, push=False, preview=preview)
    set_remote_url("origin", url, cwd=repo_dir, push=True, preview=preview)


def _ensure_additional_push_urls(
    repo_dir: str,
    mirrors: MirrorMap,
    primary: str,
    preview: bool,
) -> None:
    """
    Ensure all *git* mirror URLs (except primary) are configured as additional
    push URLs for origin.

    Non-git URLs (like PyPI) are ignored and will never land in git config.
    """
    git_only = _git_mirrors_only(mirrors)
    desired: Set[str] = {u for u in git_only.values() if u and u != primary}
    if not desired:
        return

    try:
        existing = get_remote_push_urls("origin", cwd=repo_dir)
    except GitRunError:
        existing = set()

    for url in sorted(desired - existing):
        add_remote_push_url("origin", url, cwd=repo_dir, preview=preview)


def ensure_origin_remote(
    repo: Repository,
    ctx: RepoMirrorContext,
    preview: bool,
) -> None:
    repo_dir = ctx.repo_dir

    if not os.path.isdir(os.path.join(repo_dir, ".git")):
        print(f"[WARN] {repo_dir} is not a Git repository.")
        return

    primary = determine_primary_remote_url(repo, ctx)
    if not primary or not _is_git_remote_url(primary):
        print("[WARN] No valid git primary mirror URL could be determined.")
        return

    # 1) Ensure origin exists
    if not has_origin_remote(repo_dir):
        try:
            add_remote("origin", primary, cwd=repo_dir, preview=preview)
        except GitAddRemoteError as exc:
            print(f"[WARN] Failed to add origin remote: {exc}")
            return  # without origin we cannot reliably proceed

    # 2) Ensure origin fetch+push URLs are correct
    try:
        _set_origin_fetch_and_push(repo_dir, primary, preview)
    except GitSetRemoteUrlError as exc:
        print(f"[WARN] Failed to set origin URLs: {exc}")

    # 3) Ensure additional push URLs for mirrors (git urls only)
    try:
        _ensure_additional_push_urls(repo_dir, ctx.resolved_mirrors, primary, preview)
    except GitAddRemotePushUrlError as exc:
        print(f"[WARN] Failed to add additional push URLs: {exc}")
