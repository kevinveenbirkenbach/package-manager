# src/pkgmgr/actions/mirror/setup_cmd.py
from __future__ import annotations

from typing import List, Tuple
from urllib.parse import urlparse

from pkgmgr.core.git import GitError, run_git
from pkgmgr.core.remote_provisioning import ProviderHint, RepoSpec, ensure_remote_repo
from pkgmgr.core.remote_provisioning.ensure import EnsureOptions

from .context import build_context
from .git_remote import determine_primary_remote_url, ensure_origin_remote
from .types import Repository


def _probe_mirror(url: str, repo_dir: str) -> Tuple[bool, str]:
    """
    Probe a remote mirror URL using `git ls-remote`.

    Returns:
      (True, "") on success,
      (False, error_message) on failure.
    """
    try:
        run_git(["ls-remote", url], cwd=repo_dir)
        return True, ""
    except GitError as exc:
        return False, str(exc)


def _host_from_git_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""

    if "://" in url:
        parsed = urlparse(url)
        netloc = (parsed.netloc or "").strip()
        if "@" in netloc:
            netloc = netloc.split("@", 1)[1]
        # keep optional :port
        return netloc

    # scp-like: git@host:owner/repo.git
    if "@" in url and ":" in url:
        after_at = url.split("@", 1)[1]
        host = after_at.split(":", 1)[0]
        return host.strip()

    return url.split("/", 1)[0].strip()

def _ensure_remote_repository(
    repo: Repository,
    repositories_base_dir: str,
    all_repos: List[Repository],
    preview: bool,
) -> None:
    """
    Ensure that the remote repository exists using provider APIs.

    This is ONLY called when ensure_remote=True.
    """
    ctx = build_context(repo, repositories_base_dir, all_repos)
    resolved_mirrors = ctx.resolved_mirrors

    primary_url = determine_primary_remote_url(repo, resolved_mirrors)
    if not primary_url:
        print("[INFO] No remote URL could be derived; skipping remote provisioning.")
        return

    # IMPORTANT:
    # - repo["provider"] is typically a provider *kind* (e.g. "github" / "gitea"),
    #   NOT a hostname. We derive the actual host from the remote URL.
    host = _host_from_git_url(primary_url)
    owner = repo.get("account")
    name = repo.get("repository")

    if not host or not owner or not name:
        print("[WARN] Missing host/account/repository; cannot ensure remote repo.")
        print(f"       host={host!r}, account={owner!r}, repository={name!r}")
        return

    print("------------------------------------------------------------")
    print(f"[REMOTE ENSURE] {ctx.identifier}")
    print(f"[REMOTE ENSURE] host: {host}")
    print("------------------------------------------------------------")

    spec = RepoSpec(
        host=str(host),
        owner=str(owner),
        name=str(name),
        private=bool(repo.get("private", True)),
        description=str(repo.get("description", "")),
    )

    provider_kind = str(repo.get("provider", "")).strip().lower() or None

    try:
        result = ensure_remote_repo(
            spec,
            provider_hint=ProviderHint(kind=provider_kind),
            options=EnsureOptions(
                preview=preview,
                interactive=True,
                allow_prompt=True,
                save_prompt_token_to_keyring=True,
            ),
        )
        print(f"[REMOTE ENSURE] {result.status.upper()}: {result.message}")
        if result.url:
            print(f"[REMOTE ENSURE] URL: {result.url}")
    except Exception as exc:  # noqa: BLE001
        # Keep action layer resilient
        print(f"[ERROR] Remote provisioning failed: {exc}")

    print()


def _setup_local_mirrors_for_repo(
    repo: Repository,
    repositories_base_dir: str,
    all_repos: List[Repository],
    preview: bool,
) -> None:
    """
    Local setup:
      - Ensure 'origin' remote exists and is sane
    """
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
    """
    Remote-side setup / validation.

    Default behavior:
      - Non-destructive checks using `git ls-remote`.

    Optional behavior:
      - If ensure_remote=True:
          * Attempt to create missing repositories via provider API
          * Uses TokenResolver (ENV -> keyring -> prompt)
    """
    ctx = build_context(repo, repositories_base_dir, all_repos)
    resolved_mirrors = ctx.resolved_mirrors

    print("------------------------------------------------------------")
    print(f"[MIRROR SETUP:REMOTE] {ctx.identifier}")
    print(f"[MIRROR SETUP:REMOTE] dir: {ctx.repo_dir}")
    print("------------------------------------------------------------")

    if ensure_remote:
        _ensure_remote_repository(
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

        ok, error_message = _probe_mirror(primary_url, ctx.repo_dir)
        if ok:
            print(f"[OK] primary: {primary_url}")
        else:
            print(f"[WARN] primary: {primary_url}")
            for line in error_message.splitlines():
                print(f"         {line}")

        print()
        return

    for name, url in sorted(resolved_mirrors.items()):
        ok, error_message = _probe_mirror(url, ctx.repo_dir)
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
    """
    Setup mirrors for the selected repositories.

    local:
      - Configure local Git remotes (ensure 'origin' exists).

    remote:
      - Non-destructive remote checks using `git ls-remote`.

    ensure_remote:
      - If True, attempt to create missing remote repositories via provider APIs.
      - This is explicit and NEVER enabled implicitly.
    """
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
