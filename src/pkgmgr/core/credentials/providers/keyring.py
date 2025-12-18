# src/pkgmgr/core/credentials/providers/keyring.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..store_keys import build_keyring_key
from ..types import KeyringUnavailableError, TokenRequest, TokenResult


def _import_keyring():
    """
    Import python-keyring.

    Raises:
      KeyringUnavailableError if:
        - library is missing
        - no backend is configured / usable
        - import fails for any reason
    """
    try:
        import keyring  # type: ignore
    except Exception as exc:  # noqa: BLE001
        raise KeyringUnavailableError("python-keyring is not installed.") from exc

    # Some environments have keyring installed but no usable backend.
    # We do a lightweight "backend sanity check" by attempting to read the backend.
    try:
        _ = keyring.get_keyring()
    except Exception as exc:  # noqa: BLE001
        raise KeyringUnavailableError(
            "python-keyring is installed but no usable keyring backend is configured."
        ) from exc

    return keyring


@dataclass(frozen=True)
class KeyringTokenProvider:
    """Resolve/store tokens from/to OS keyring via python-keyring."""

    source_name: str = "keyring"

    def get(self, request: TokenRequest) -> Optional[TokenResult]:
        keyring = _import_keyring()
        key = build_keyring_key(request.provider_kind, request.host, request.owner)
        token = keyring.get_password(key.service, key.username)
        if token:
            return TokenResult(token=token.strip(), source=self.source_name)
        return None

    def set(self, request: TokenRequest, token: str) -> None:
        keyring = _import_keyring()
        key = build_keyring_key(request.provider_kind, request.host, request.owner)
        keyring.set_password(key.service, key.username, token)
