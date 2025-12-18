# src/pkgmgr/core/credentials/store_keys.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class KeyringKey:
    """Keyring address for a token."""

    service: str
    username: str


def build_keyring_key(
    provider_kind: str, host: str, owner: Optional[str]
) -> KeyringKey:
    """Build a stable keyring key.

    - service: "pkgmgr:<provider>"
    - username: "<host>|<owner>" or "<host>|-"
    """
    provider_kind = str(provider_kind).strip().lower()
    host = str(host).strip()
    owner_part = str(owner).strip() if owner else "-"
    return KeyringKey(
        service=f"pkgmgr:{provider_kind}", username=f"{host}|{owner_part}"
    )


def env_var_candidates(
    provider_kind: str, host: str, owner: Optional[str]
) -> list[str]:
    """Return a list of environment variable names to try.

    Order is from most specific to most generic.
    """
    kind = re_sub_non_alnum(str(provider_kind).strip().upper())
    host_norm = re_sub_non_alnum(str(host).strip().upper())
    candidates: list[str] = []

    if owner:
        owner_norm = re_sub_non_alnum(str(owner).strip().upper())
        candidates.append(f"PKGMGR_{kind}_TOKEN_{host_norm}_{owner_norm}")
        candidates.append(f"PKGMGR_TOKEN_{kind}_{host_norm}_{owner_norm}")

    candidates.append(f"PKGMGR_{kind}_TOKEN_{host_norm}")
    candidates.append(f"PKGMGR_TOKEN_{kind}_{host_norm}")
    candidates.append(f"PKGMGR_{kind}_TOKEN")
    candidates.append(f"PKGMGR_TOKEN_{kind}")
    candidates.append("PKGMGR_TOKEN")

    return candidates


def re_sub_non_alnum(value: str) -> str:
    """Normalize to an uppercase env-var friendly token (A-Z0-9_)."""
    import re

    return re.sub(r"[^A-Z0-9]+", "_", value).strip("_")
