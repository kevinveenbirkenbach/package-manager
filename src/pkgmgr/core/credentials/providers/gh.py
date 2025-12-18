from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional

from ..types import TokenRequest, TokenResult


@dataclass(frozen=True)
class GhTokenProvider:
    """
    Resolve a GitHub token via GitHub CLI (`gh auth token`).

    This does NOT persist anything; it only reads what `gh` already knows.
    """

    source_name: str = "gh"

    def get(self, request: TokenRequest) -> Optional[TokenResult]:
        # Only meaningful for GitHub-like providers
        kind = (request.provider_kind or "").strip().lower()
        if kind not in ("github", "github.com"):
            return None

        if not shutil.which("gh"):
            return None

        host = (request.host or "").strip() or "github.com"

        try:
            out = subprocess.check_output(
                ["gh", "auth", "token", "--hostname", host],
                stderr=subprocess.STDOUT,
                text=True,
            ).strip()
        except Exception:
            return None

        if not out:
            return None

        return TokenResult(token=out, source=self.source_name)
