# src/pkgmgr/actions/mirror/remote_provision.py
from __future__ import annotations

from typing import List

from pkgmgr.core.remote_provisioning import ProviderHint, RepoSpec, ensure_remote_repo
from pkgmgr.core.remote_provisioning.ensure import EnsureOptions

from .context import build_context
from .git_remote import determine_primary_remote_url
from .types import Repository
from .url_utils import hostport_from_git_url, normalize_provider_host


def ensure_remote_repository(
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

    host_raw, _port = hostport_from_git_url(primary_url)
    host = normalize_provider_host(host_raw)

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
        print(f"[ERROR] Remote provisioning failed: {exc}")

    print()
