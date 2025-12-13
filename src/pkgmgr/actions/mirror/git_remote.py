from __future__ import annotations

import os

from pkgmgr.core.command.run import run_command
from pkgmgr.core.git import GitError, run_git
from typing import List, Optional, Set

from .types import MirrorMap, RepoMirrorContext, Repository


def build_default_ssh_url(repo: Repository) -> Optional[str]:
    """
    Build a simple SSH URL from repo config if no explicit mirror is defined.

    Example: git@github.com:account/repository.git
    """
    provider = repo.get("provider")
    account = repo.get("account")
    name = repo.get("repository")
    port = repo.get("port")

    if not provider or not account or not name:
        return None

    provider = str(provider)
    account = str(account)
    name = str(name)

    if port:
        return f"ssh://git@{provider}:{port}/{account}/{name}.git"

    # GitHub-style shorthand
    return f"git@{provider}:{account}/{name}.git"


def determine_primary_remote_url(
    repo: Repository,
    resolved_mirrors: MirrorMap,
) -> Optional[str]:
    """
    Determine the primary remote URL in a consistent way:

      1. resolved_mirrors["origin"]
      2. any resolved mirror (first by name)
      3. default SSH URL from provider/account/repository
    """
    if "origin" in resolved_mirrors:
        return resolved_mirrors["origin"]

    if resolved_mirrors:
        first_name = sorted(resolved_mirrors.keys())[0]
        return resolved_mirrors[first_name]

    return build_default_ssh_url(repo)


def _safe_git_output(args: List[str], cwd: str) -> Optional[str]:
    """
    Run a Git command via run_git and return its stdout, or None on failure.
    """
    try:
        return run_git(args, cwd=cwd)
    except GitError:
        return None


def current_origin_url(repo_dir: str) -> Optional[str]:
    """
    Return the current URL for remote 'origin', or None if not present.
    """
    output = _safe_git_output(["remote", "get-url", "origin"], cwd=repo_dir)
    if not output:
        return None
    url = output.strip()
    return url or None


def has_origin_remote(repo_dir: str) -> bool:
    """
    Check whether a remote called 'origin' exists in the repository.
    """
    output = _safe_git_output(["remote"], cwd=repo_dir)
    if not output:
        return False
    names = output.split()
    return "origin" in names


def _ensure_push_urls_for_origin(
    repo_dir: str,
    mirrors: MirrorMap,
    preview: bool,
) -> None:
    """
    Ensure that all mirror URLs are present as push URLs on 'origin'.
    """
    desired: Set[str] = {url for url in mirrors.values() if url}
    if not desired:
        return

    existing_output = _safe_git_output(
        ["remote", "get-url", "--push", "--all", "origin"],
        cwd=repo_dir,
    )
    existing = set(existing_output.splitlines()) if existing_output else set()

    missing = sorted(desired - existing)
    for url in missing:
        cmd = f"git remote set-url --add --push origin {url}"
        if preview:
            print(f"[PREVIEW] Would run in {repo_dir!r}: {cmd}")
        else:
            print(f"[INFO] Adding push URL to 'origin': {url}")
            run_command(cmd, cwd=repo_dir, preview=False)


def ensure_origin_remote(
    repo: Repository,
    ctx: RepoMirrorContext,
    preview: bool,
) -> None:
    """
    Ensure that a usable 'origin' remote exists and has all push URLs.
    """
    repo_dir = ctx.repo_dir
    resolved_mirrors = ctx.resolved_mirrors

    if not os.path.isdir(os.path.join(repo_dir, ".git")):
        print(f"[WARN] {repo_dir} is not a Git repository (no .git directory).")
        return

    url = determine_primary_remote_url(repo, resolved_mirrors)

    if not has_origin_remote(repo_dir):
        if not url:
            print(
                "[WARN] Could not determine URL for 'origin' remote. "
                "Please configure mirrors or provider/account/repository."
            )
            return

        cmd = f"git remote add origin {url}"
        if preview:
            print(f"[PREVIEW] Would run in {repo_dir!r}: {cmd}")
        else:
            print(f"[INFO] Adding 'origin' remote in {repo_dir}: {url}")
            run_command(cmd, cwd=repo_dir, preview=False)
    else:
        current = current_origin_url(repo_dir)
        if current == url or not url:
            print(
                "[INFO] 'origin' already points to "
                f"{current or '<unknown>'} (no change needed)."
            )
        else:
            # We do not auto-change origin here, only log the mismatch.
            print(
                "[INFO] 'origin' exists with URL "
                f"{current or '<unknown>'}; not changing to {url}."
            )

    # Ensure all mirrors are present as push URLs
    _ensure_push_urls_for_origin(repo_dir, resolved_mirrors, preview)


def is_remote_reachable(url: str, cwd: Optional[str] = None) -> bool:
    """
    Check whether a remote repository is reachable via `git ls-remote`.

    This does NOT modify anything; it only probes the remote.
    """
    workdir = cwd or os.getcwd()
    try:
        # --exit-code → non-zero exit code if the remote does not exist
        run_git(["ls-remote", "--exit-code", url], cwd=workdir)
        return True
    except GitError:
        return False
