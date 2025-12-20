from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

EnsureStatus = Literal[
    "exists",
    "created",
    "updated",
    "noop",
    "notfound",
    "skipped",
    "failed",
]


@dataclass(frozen=True)
class ProviderHint:
    """Optional hint to force a provider kind."""

    kind: Optional[str] = None  # e.g. "gitea" or "github"


@dataclass(frozen=True)
class RepoSpec:
    """Desired remote repository."""

    host: str
    owner: str
    name: str
    private: bool = True
    description: str = ""
    default_branch: Optional[str] = None


@dataclass(frozen=True)
class EnsureResult:
    status: EnsureStatus
    message: str
    url: Optional[str] = None


class RemoteProvisioningError(RuntimeError):
    """Base class for remote provisioning errors."""


class AuthError(RemoteProvisioningError):
    """Authentication failed (401)."""


class PermissionError(RemoteProvisioningError):
    """Permission denied (403)."""


class NotFoundError(RemoteProvisioningError):
    """Resource not found (404)."""


class PolicyError(RemoteProvisioningError):
    """Provider/org policy prevents the operation."""


class NetworkError(RemoteProvisioningError):
    """Network/transport errors."""


class UnsupportedProviderError(RemoteProvisioningError):
    """No provider matched for the given host."""
