from __future__ import annotations

import os
from typing import List, Optional, Set

from pkgmgr.core.command.run import run_command
from pkgmgr.core.git import GitError, run_git

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


def _safe_git_output(args: List[str], cwd: str) -> Optional[str]:
    try:
        return run_git(args, cwd=cwd)
    except GitError:
        return None


def has_origin_remote(repo_dir: str) -> bool:
    out = _safe_git_output(["remote"], cwd=repo_dir)
    return bool(out and "origin" in out.split())


def _set_origin_fetch_and_push(repo_dir: str, url: str, preview: bool) -> None:
    fetch = f"git remote set-url origin {url}"
    push = f"git remote set-url --push origin {url}"

    if preview:
        print(f"[PREVIEW] Would run in {repo_dir!r}: {fetch}")
        print(f"[PREVIEW] Would run in {repo_dir!r}: {push}")
        return

    run_command(fetch, cwd=repo_dir, preview=False)
    run_command(push, cwd=repo_dir, preview=False)


def _ensure_additional_push_urls(
    repo_dir: str,
    mirrors: MirrorMap,
    primary: str,
    preview: bool,
) -> None:
    desired: Set[str] = {u for u in mirrors.values() if u and u != primary}
    if not desired:
        return

    out = _safe_git_output(
        ["remote", "get-url", "--push", "--all", "origin"],
        cwd=repo_dir,
    )
    existing = set(out.splitlines()) if out else set()

    for url in sorted(desired - existing):
        cmd = f"git remote set-url --add --push origin {url}"
        if preview:
            print(f"[PREVIEW] Would run in {repo_dir!r}: {cmd}")
        else:
            run_command(cmd, cwd=repo_dir, preview=False)


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

    if not has_origin_remote(repo_dir):
        cmd = f"git remote add origin {primary}"
        if preview:
            print(f"[PREVIEW] Would run in {repo_dir!r}: {cmd}")
        else:
            run_command(cmd, cwd=repo_dir, preview=False)

        _set_origin_fetch_and_push(repo_dir, primary, preview)

    _ensure_additional_push_urls(repo_dir, ctx.resolved_mirrors, primary, preview)


def is_remote_reachable(url: str, cwd: Optional[str] = None) -> bool:
    try:
        run_git(["ls-remote", "--exit-code", url], cwd=cwd or os.getcwd())
        return True
    except GitError:
        return False
