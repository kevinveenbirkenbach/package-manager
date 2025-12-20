from __future__ import annotations

from abc import ABC, abstractmethod

from ..types import EnsureResult, RepoSpec


class RemoteProvider(ABC):
    """Provider interface for remote repo provisioning."""

    kind: str

    @abstractmethod
    def can_handle(self, host: str) -> bool:
        """Return True if this provider implementation matches the host."""

    @abstractmethod
    def repo_exists(self, token: str, spec: RepoSpec) -> bool:
        """Return True if repo exists and is accessible."""

    @abstractmethod
    def create_repo(self, token: str, spec: RepoSpec) -> EnsureResult:
        """Create a repository (owner may be user or org)."""

    @abstractmethod
    def get_repo_private(self, token: str, spec: RepoSpec) -> bool | None:
        """
        Return current repo privacy, or None if repo not found / inaccessible.

        IMPORTANT:
        - Must NOT create repositories.
        - Should return None on 404 (not found) or when the repo cannot be accessed.
        """

    @abstractmethod
    def set_repo_private(self, token: str, spec: RepoSpec, *, private: bool) -> None:
        """
        Update repo privacy (PATCH). Must NOT create repositories.

        Implementations should raise HttpError on API failure.
        """

    def ensure_repo(self, token: str, spec: RepoSpec) -> EnsureResult:
        """Ensure repository exists (create if missing)."""
        if self.repo_exists(token, spec):
            return EnsureResult(status="exists", message="Repository exists.")
        return self.create_repo(token, spec)

    @staticmethod
    def _api_base(host: str) -> str:
        # Default to https. If you need http for local dev, store host as "http://..."
        if host.startswith("http://") or host.startswith("https://"):
            return host.rstrip("/")
        return f"https://{host}".rstrip("/")
