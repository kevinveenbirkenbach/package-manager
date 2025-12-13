# src/pkgmgr/core/remote_provisioning/registry.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .providers.base import RemoteProvider
from .providers.gitea import GiteaProvider
from .providers.github import GitHubProvider


@dataclass
class ProviderRegistry:
    """Resolve the correct provider implementation for a host."""

    providers: List[RemoteProvider]

    @classmethod
    def default(cls) -> "ProviderRegistry":
        # Order matters: more specific providers first; fallback providers last.
        return cls(providers=[GitHubProvider(), GiteaProvider()])

    def resolve(self, host: str) -> Optional[RemoteProvider]:
        for p in self.providers:
            try:
                if p.can_handle(host):
                    return p
            except Exception:
                continue
        return None
