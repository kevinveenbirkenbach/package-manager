from __future__ import annotations

import urllib.request
import json


def validate_token(provider_kind: str, host: str, token: str) -> bool:
    """
    Return True if token appears valid for the provider.
    Currently implemented for GitHub only.
    """
    kind = (provider_kind or "").strip().lower()
    host = (host or "").strip() or "github.com"
    token = (token or "").strip()
    if not token:
        return False

    if kind in ("github", "github.com") and host.lower() == "github.com":
        req = urllib.request.Request(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "User-Agent": "pkgmgr",
            },
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status != 200:
                    return False
                # Optional: parse to ensure body is JSON
                _ = json.loads(resp.read().decode("utf-8"))
                return True
        except Exception:
            return False

    # Unknown provider: don't hard-fail validation (conservative default)
    # If you prefer strictness: return False here.
    return True
