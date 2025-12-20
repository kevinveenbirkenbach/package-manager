from __future__ import annotations

from typing import List

from pkgmgr.core.git.queries import probe_remote_reachable_detail
from pkgmgr.core.remote_provisioning import ProviderHint, RepoSpec, set_repo_visibility
from pkgmgr.core.remote_provisioning.visibility import VisibilityOptions

from .context import build_context
from .git_remote import determine_primary_remote_url, ensure_origin_remote
from .remote_provision import ensure_remote_repository_for_url
from .types import Repository
from .url_utils import normalize_provider_host, parse_repo_from_git_url


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


def _provider_hint_from_host(host: str) -> str | None:
    h = (host or "").lower()
    if h == "github.com":
        return "github"
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
    ensure_visibility: str | None,
) -> None:
    ctx = build_context(repo, repositories_base_dir, all_repos)

    print("------------------------------------------------------------")
    print(f"[MIRROR SETUP:REMOTE] {ctx.identifier}")
    print(f"[MIRROR SETUP:REMOTE] dir: {ctx.repo_dir}")
    print("------------------------------------------------------------")

    git_mirrors = {
        k: v for k, v in ctx.resolved_mirrors.items() if _is_git_remote_url(v)
    }

    def _desired_private_default() -> bool:
        # default behavior: repo['private'] (or True)
        if ensure_visibility == "public":
            return False
        if ensure_visibility == "private":
            return True
        return bool(repo.get("private", True))

    def _should_enforce_visibility() -> bool:
        return ensure_visibility in ("public", "private")

    def _visibility_private_value() -> bool:
        return ensure_visibility == "private"

    description = str(repo.get("description", ""))

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
                private_default=_desired_private_default(),
                description=description,
                preview=preview,
            )
            # IMPORTANT: enforce visibility only if requested
            if _should_enforce_visibility():
                _apply_visibility_for_url(
                    url=primary,
                    private=_visibility_private_value(),
                    description=description,
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
                private_default=_desired_private_default(),
                description=description,
                preview=preview,
            )
            if _should_enforce_visibility():
                _apply_visibility_for_url(
                    url=url,
                    private=_visibility_private_value(),
                    description=description,
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
    ensure_visibility: str | None = None,
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
                ensure_visibility,
            )
