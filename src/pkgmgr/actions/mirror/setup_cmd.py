from __future__ import annotations

from typing import List

from .context import build_context
from .git_remote import determine_primary_remote_url, ensure_origin_remote
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
) -> None:
    """
    Placeholder for remote-side setup.

    This is intentionally conservative:
      - We *do not* call any provider APIs automatically here.
      - Instead, we show what should exist and which URL should be created.
    """
    ctx = build_context(repo, repositories_base_dir, all_repos)
    resolved_m = ctx.resolved_mirrors

    primary_url = determine_primary_remote_url(repo, resolved_m)

    print("------------------------------------------------------------")
    print(f"[MIRROR SETUP:REMOTE] {ctx.identifier}")
    print(f"[MIRROR SETUP:REMOTE] dir: {ctx.repo_dir}")
    print("------------------------------------------------------------")

    if not primary_url:
        print(
            "[WARN] Could not determine primary remote URL for this repository.\n"
            "       Please ensure provider/account/repository and/or mirrors "
            "are set in your config."
        )
        print()
        return

    if preview:
        print(
            "[PREVIEW] Would ensure that a remote repository exists for:\n"
            f"          {primary_url}\n"
            "          (Provider-specific API calls not implemented yet.)"
        )
    else:
        print(
            "[INFO] Remote-setup logic is not implemented yet.\n"
            "       Please create the remote repository manually if needed:\n"
            f"         {primary_url}\n"
        )

    print()


def setup_mirrors(
    selected_repos: List[Repository],
    repositories_base_dir: str,
    all_repos: List[Repository],
    preview: bool = False,
    local: bool = True,
    remote: bool = True,
) -> None:
    """
    Setup mirrors for the selected repositories.

    local:
      - Configure local Git remotes (currently: ensure 'origin' is present and
        points to a reasonable URL).

    remote:
      - Placeholder that prints what should exist on the remote side.
        Actual API calls to providers are not implemented yet.
    """
    for repo in selected_repos:
        if local:
            _setup_local_mirrors_for_repo(
                repo,
                repositories_base_dir=repositories_base_dir,
                all_repos=all_repos,
                preview=preview,
            )

        if remote:
            _setup_remote_mirrors_for_repo(
                repo,
                repositories_base_dir=repositories_base_dir,
                all_repos=all_repos,
                preview=preview,
            )
