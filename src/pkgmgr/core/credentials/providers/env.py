# src/pkgmgr/core/credentials/providers/env.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from ..store_keys import env_var_candidates
from ..types import TokenRequest, TokenResult


@dataclass(frozen=True)
class EnvTokenProvider:
    """Resolve tokens from environment variables."""

    source_name: str = "env"

    def get(self, request: TokenRequest) -> Optional[TokenResult]:
        for key in env_var_candidates(
            request.provider_kind, request.host, request.owner
        ):
            val = os.environ.get(key)
            if val:
                return TokenResult(token=val.strip(), source=self.source_name)
        return None
