# src/pkgmgr/core/credentials/types.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class CredentialError(RuntimeError):
    """Base class for credential resolution errors."""


class NoCredentialsError(CredentialError):
    """Raised when no usable credential could be resolved."""


class KeyringUnavailableError(CredentialError):
    """Raised when keyring is requested but no backend is available."""


@dataclass(frozen=True)
class TokenRequest:
    """Parameters describing which token we need."""

    provider_kind: str  # e.g. "gitea", "github"
    host: str  # e.g. "git.example.org" or "github.com"
    owner: Optional[str] = None  # optional org/user


@dataclass(frozen=True)
class TokenResult:
    """A resolved token plus metadata about its source."""

    token: str
    source: str  # "env" | "keyring" | "prompt"
