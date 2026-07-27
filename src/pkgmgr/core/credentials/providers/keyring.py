# src/pkgmgr/core/credentials/providers/keyring.py
from __future__ import annotations

from dataclasses import dataclass

from ..store_keys import build_keyring_key
from ..types import (
    KeyringOperationError,
    KeyringUnavailableError,
    TokenRequest,
    TokenResult,
)


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
    except Exception as exc:
        raise KeyringUnavailableError("python-keyring is not installed.") from exc

    # Some environments have keyring installed but no usable backend.
    # We do a lightweight "backend sanity check" by attempting to read the backend.
    try:
        _ = keyring.get_keyring()
    except Exception as exc:
        raise KeyringUnavailableError(
            "python-keyring is installed but no usable keyring backend is configured."
        ) from exc

    return keyring


@dataclass(frozen=True)
class KeyringTokenProvider:
    """Resolve/store tokens from/to OS keyring via python-keyring."""

    source_name: str = "keyring"

    def get(self, request: TokenRequest) -> TokenResult | None:
        keyring = _import_keyring()
        key = build_keyring_key(request.provider_kind, request.host, request.owner)
        try:
            token = keyring.get_password(key.service, key.username)
        except Exception as exc:
            raise KeyringOperationError(
                f"Reading the keyring entry for {key.service!r} failed."
            ) from exc
        if token:
            return TokenResult(token=token.strip(), source=self.source_name)
        return None

    def set(self, request: TokenRequest, token: str) -> None:
        keyring = _import_keyring()
        key = build_keyring_key(request.provider_kind, request.host, request.owner)
        try:
            keyring.set_password(key.service, key.username, token)
        except Exception as exc:
            raise KeyringOperationError(
                f"Writing the keyring entry for {key.service!r} failed."
            ) from exc
