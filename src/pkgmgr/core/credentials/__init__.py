# src/pkgmgr/core/credentials/__init__.py
"""Credential resolution for provider APIs."""

from .resolver import ResolutionOptions, TokenResolver
from .types import (
    CredentialError,
    KeyringUnavailableError,
    NoCredentialsError,
    TokenRequest,
    TokenResult,
)

__all__ = [
    "TokenResolver",
    "ResolutionOptions",
    "CredentialError",
    "NoCredentialsError",
    "KeyringUnavailableError",
    "TokenRequest",
    "TokenResult",
]
