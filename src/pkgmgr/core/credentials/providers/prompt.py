# src/pkgmgr/core/credentials/providers/prompt.py
from __future__ import annotations

import sys
from dataclasses import dataclass
from getpass import getpass
from typing import Optional

from ..types import TokenRequest, TokenResult


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
        prompt = f"Enter API token for {request.provider_kind} on {request.host}{owner_info}: "
        token = (getpass(prompt) or "").strip()
        if not token:
            return None
        return TokenResult(token=token, source=self.source_name)
