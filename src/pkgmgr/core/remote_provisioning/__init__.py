# src/pkgmgr/core/remote_provisioning/__init__.py
"""Remote repository provisioning (ensure remote repo exists)."""

from .ensure import ensure_remote_repo
from .registry import ProviderRegistry
from .types import EnsureResult, ProviderHint, RepoSpec

__all__ = [
    "ensure_remote_repo",
    "RepoSpec",
    "EnsureResult",
    "ProviderHint",
    "ProviderRegistry",
]
