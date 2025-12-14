from __future__ import annotations

from typing import List

from pkgmgr.core.remote_provisioning import ProviderHint, RepoSpec, ensure_remote_repo
from pkgmgr.core.remote_provisioning.ensure import EnsureOptions

from .context import build_context
from .git_remote import determine_primary_remote_url
from .types import Repository
from .url_utils import normalize_provider_host, parse_repo_from_git_url


def ensure_remote_repository(
    repo: Repository,
    repositories_base_dir: str,
    all_repos: List[Repository],
    preview: bool,
) -> None:
    ctx = build_context(repo, repositories_base_dir, all_repos)

    primary_url = determine_primary_remote_url(repo, ctx)
    if not primary_url:
        print("[INFO] No primary URL found; skipping remote provisioning.")
        return

    host_raw, owner, name = parse_repo_from_git_url(primary_url)
    host = normalize_provider_host(host_raw)

    if not host or not owner or not name:
        print("[WARN] Could not parse remote URL:", primary_url)
        return

    spec = RepoSpec(
        host=host,
        owner=owner,
        name=name,
        private=bool(repo.get("private", True)),
        description=str(repo.get("description", "")),
    )

    provider_kind = str(repo.get("provider", "")).lower() or None

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
