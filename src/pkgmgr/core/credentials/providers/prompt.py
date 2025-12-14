# src/pkgmgr/core/credentials/providers/prompt.py
from __future__ import annotations

import sys
from dataclasses import dataclass
from getpass import getpass
from typing import Optional

from ..types import TokenRequest, TokenResult


def _token_help_url(provider_kind: str, host: str) -> Optional[str]:
    """
    Return a provider-specific URL where a user can create/get an API token.

    Keep this conservative and stable:
    - GitHub: official token settings URL
    - Gitea/Forgejo: common settings path on the given host
    - GitLab: common personal access token path
    """
    kind = (provider_kind or "").strip().lower()
    h = (host or "").strip()

    # GitHub (cloud)
    if kind == "github":
        return "https://github.com/settings/tokens"

    # Gitea / Forgejo (self-hosted)
    if kind in ("gitea", "forgejo"):
        # Typical UI path: Settings -> Applications -> Access Tokens
        # In many installations this is available at /user/settings/applications
        base = f"https://{h}".rstrip("/")
        return f"{base}/user/settings/applications"

    # GitLab (cloud or self-hosted)
    if kind == "gitlab":
        base = "https://gitlab.com" if not h else f"https://{h}".rstrip("/")
        return f"{base}/-/profile/personal_access_tokens"

    return None


@dataclass(frozen=True)
class PromptTokenProvider:
    """Interactively prompt for a token.

    Only used when:
    - interactive mode is enabled
    - stdin is a TTY
    """

    source_name: str = "prompt"

    def get(self, request: TokenRequest) -> Optional[TokenResult]:
        if not sys.stdin.isatty():
            return None

        owner_info = f" (owner: {request.owner})" if request.owner else ""
        help_url = _token_help_url(request.provider_kind, request.host)

        if help_url:
            print(f"[INFO] Create/get your token here: {help_url}")

        prompt = f"Enter API token for {request.provider_kind} on {request.host}{owner_info}: "
        token = (getpass(prompt) or "").strip()
        if not token:
            return None
        return TokenResult(token=token, source=self.source_name)
