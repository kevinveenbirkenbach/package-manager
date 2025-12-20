from __future__ import annotations

from typing import List

from pkgmgr.core.remote_provisioning import ProviderHint, RepoSpec, set_repo_visibility
from pkgmgr.core.remote_provisioning.visibility import VisibilityOptions

from .context import build_context
from .git_remote import determine_primary_remote_url
from .types import Repository
from .url_utils import normalize_provider_host, parse_repo_from_git_url


def _is_git_remote_url(url: str) -> bool:
    # Keep same semantics as setup_cmd.py / git_remote.py
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


def _provider_hint_from_host(host: str) -> str | None:
    h = (host or "").lower()
    if h == "github.com":
        return "github"
    # Best-effort default for self-hosted git domains
    return "gitea" if h else None


def _apply_visibility_for_url(
    *,
    url: str,
    private: bool,
    description: str,
    preview: bool,
) -> None:
    host_raw, owner, name = parse_repo_from_git_url(url)
    host = normalize_provider_host(host_raw)

    if not host or not owner or not name:
        print(f"[WARN] Could not parse repo from URL: {url}")
        return

    spec = RepoSpec(
        host=host,
        owner=owner,
        name=name,
        private=private,
        description=description,
    )

    provider_kind = _provider_hint_from_host(host)
    res = set_repo_visibility(
        spec,
        private=private,
        provider_hint=ProviderHint(kind=provider_kind),
        options=VisibilityOptions(preview=preview),
    )
    print(f"[REMOTE VISIBILITY] {res.status.upper()}: {res.message}")


def set_mirror_visibility(
    selected_repos: List[Repository],
    repositories_base_dir: str,
    all_repos: List[Repository],
    *,
    visibility: str,
    preview: bool = False,
) -> None:
    """
    Set remote repository visibility for all git mirrors of each selected repo.

    visibility:
      - "private"
      - "public"
    """
    v = (visibility or "").strip().lower()
    if v not in ("private", "public"):
        raise ValueError("visibility must be 'private' or 'public'")

    desired_private = v == "private"

    for repo in selected_repos:
        ctx = build_context(repo, repositories_base_dir, all_repos)

        print("------------------------------------------------------------")
        print(f"[MIRROR VISIBILITY] {ctx.identifier}")
        print(f"[MIRROR VISIBILITY] dir: {ctx.repo_dir}")
        print(f"[MIRROR VISIBILITY] target: {v}")
        print("------------------------------------------------------------")

        git_mirrors = {
            name: url
            for name, url in ctx.resolved_mirrors.items()
            if url and _is_git_remote_url(url)
        }

        # If there are no git mirrors, fall back to primary (git) URL.
        if not git_mirrors:
            primary = determine_primary_remote_url(repo, ctx)
            if not primary or not _is_git_remote_url(primary):
                print(
                    "[INFO] No git mirrors found (and no primary git URL). Nothing to do."
                )
                print()
                continue

            print(f"[MIRROR VISIBILITY] applying to primary: {primary}")
            _apply_visibility_for_url(
                url=primary,
                private=desired_private,
                description=str(repo.get("description", "")),
                preview=preview,
            )
            print()
            continue

        # Apply to ALL git mirrors
        for name, url in git_mirrors.items():
            print(f"[MIRROR VISIBILITY] applying to mirror {name!r}: {url}")
            _apply_visibility_for_url(
                url=url,
                private=desired_private,
                description=str(repo.get("description", "")),
                preview=preview,
            )

        print()
