# src/pkgmgr/actions/mirror/url_utils.py
from __future__ import annotations

from urllib.parse import urlparse
from typing import Optional, Tuple


def hostport_from_git_url(url: str) -> Tuple[str, Optional[str]]:
    """
    Extract (host, port) from common Git remote URL formats.

    Supports:
      - ssh://git@host:2201/owner/repo.git
      - https://host/owner/repo.git
      - git@host:owner/repo.git   (scp-like; no explicit port)
    """
    url = (url or "").strip()
    if not url:
        return "", None

    if "://" in url:
        parsed = urlparse(url)
        netloc = (parsed.netloc or "").strip()
        if "@" in netloc:
            netloc = netloc.split("@", 1)[1]

        # IPv6 bracket form: [::1]:2222
        if netloc.startswith("[") and "]" in netloc:
            host = netloc[1:netloc.index("]")]
            rest = netloc[netloc.index("]") + 1 :]
            port = rest[1:] if rest.startswith(":") else None
            return host.strip(), (port.strip() if port else None)

        if ":" in netloc:
            host, port = netloc.rsplit(":", 1)
            return host.strip(), (port.strip() or None)

        return netloc.strip(), None

    # scp-like: git@host:owner/repo.git
    if "@" in url and ":" in url:
        after_at = url.split("@", 1)[1]
        host = after_at.split(":", 1)[0].strip()
        return host, None

    host = url.split("/", 1)[0].strip()
    return host, None


def normalize_provider_host(host: str) -> str:
    """
    Normalize host for provider matching:
      - strip brackets
      - strip optional :port
      - lowercase
    """
    host = (host or "").strip()
    if not host:
        return ""

    if host.startswith("[") and "]" in host:
        host = host[1:host.index("]")]

    if ":" in host and host.count(":") == 1:
        host = host.rsplit(":", 1)[0]

    return host.strip().lower()
