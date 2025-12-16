from __future__ import annotations

import os
from typing import Optional, Set

from pkgmgr.core.git.errors import GitError
from pkgmgr.core.git.commands import (
    GitAddRemoteError,
    GitAddRemotePushUrlError,
    GitSetRemoteUrlError,
    add_remote,
    add_remote_push_url,
    set_remote_url,
)
from pkgmgr.core.git.queries import (
    get_remote_push_urls,
    list_remotes,
)

from .types import MirrorMap, RepoMirrorContext, Repository


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


def determine_primary_remote_url(
    repo: Repository,
    ctx: RepoMirrorContext,
) -> Optional[str]:
    """
    Priority order:
      1. origin from resolved mirrors
      2. MIRRORS file order
      3. config mirrors order
      4. default SSH URL
    """
    resolved = ctx.resolved_mirrors

    if resolved.get("origin"):
        return resolved["origin"]

    for mirrors in (ctx.file_mirrors, ctx.config_mirrors):
        for _, url in mirrors.items():
            if url:
                return url

    return build_default_ssh_url(repo)


def has_origin_remote(repo_dir: str) -> bool:
    try:
        return "origin" in list_remotes(cwd=repo_dir)
    except GitError:
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
    Ensure all mirror URLs (except primary) are configured as additional push URLs for origin.
    Preview is handled by the underlying git runner.
    """
    desired: Set[str] = {u for u in mirrors.values() if u and u != primary}
    if not desired:
        return

    try:
        existing = get_remote_push_urls("origin", cwd=repo_dir)
    except GitError:
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
    if not primary:
        print("[WARN] No primary mirror URL could be determined.")
        return

    # 1) Ensure origin exists
    if not has_origin_remote(repo_dir):
        try:
            add_remote("origin", primary, cwd=repo_dir, preview=preview)
        except GitAddRemoteError as exc:
            print(f"[WARN] Failed to add origin remote: {exc}")
            return  # without origin we cannot reliably proceed

    # 2) Ensure origin fetch+push URLs are correct (ALWAYS, even if origin already existed)
    try:
        _set_origin_fetch_and_push(repo_dir, primary, preview)
    except GitSetRemoteUrlError as exc:
        # Do not abort: still try to add additional push URLs
        print(f"[WARN] Failed to set origin URLs: {exc}")

    # 3) Ensure additional push URLs for mirrors
    try:
        _ensure_additional_push_urls(repo_dir, ctx.resolved_mirrors, primary, preview)
    except GitAddRemotePushUrlError as exc:
        print(f"[WARN] Failed to add additional push URLs: {exc}")
