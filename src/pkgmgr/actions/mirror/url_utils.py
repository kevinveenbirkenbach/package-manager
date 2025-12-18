# src/pkgmgr/actions/mirror/url_utils.py
from __future__ import annotations

from urllib.parse import urlparse
from typing import Optional, Tuple


def hostport_from_git_url(url: str) -> Tuple[str, Optional[str]]:
    url = (url or "").strip()
    if not url:
        return "", None

    if "://" in url:
        parsed = urlparse(url)
        netloc = (parsed.netloc or "").strip()
        if "@" in netloc:
            netloc = netloc.split("@", 1)[1]

        if netloc.startswith("[") and "]" in netloc:
            host = netloc[1 : netloc.index("]")]
            rest = netloc[netloc.index("]") + 1 :]
            port = rest[1:] if rest.startswith(":") else None
            return host.strip(), (port.strip() if port else None)

        if ":" in netloc:
            host, port = netloc.rsplit(":", 1)
            return host.strip(), (port.strip() or None)

        return netloc.strip(), None

    if "@" in url and ":" in url:
        after_at = url.split("@", 1)[1]
        host = after_at.split(":", 1)[0].strip()
        return host, None

    host = url.split("/", 1)[0].strip()
    return host, None


def normalize_provider_host(host: str) -> str:
    host = (host or "").strip()
    if not host:
        return ""

    if host.startswith("[") and "]" in host:
        host = host[1 : host.index("]")]

    if ":" in host and host.count(":") == 1:
        host = host.rsplit(":", 1)[0]

    return host.strip().lower()


def _strip_dot_git(name: str) -> str:
    n = (name or "").strip()
    if n.lower().endswith(".git"):
        return n[:-4]
    return n


def parse_repo_from_git_url(url: str) -> Tuple[str, Optional[str], Optional[str]]:
    """
    Parse (host, owner, repo_name) from common Git remote URLs.

    Supports:
      - ssh://git@host:2201/owner/repo.git
      - https://host/owner/repo.git
      - git@host:owner/repo.git
      - host/owner/repo(.git) (best-effort)

    Returns:
      (host, owner, repo_name) with owner/repo possibly None if not derivable.
    """
    u = (url or "").strip()
    if not u:
        return "", None, None

    # URL-style (ssh://, https://, http://)
    if "://" in u:
        parsed = urlparse(u)
        host = (parsed.hostname or "").strip()
        path = (parsed.path or "").strip("/")
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 2:
            owner = parts[0]
            repo_name = _strip_dot_git(parts[1])
            return host, owner, repo_name
        return host, None, None

    # SCP-like: git@host:owner/repo.git
    if "@" in u and ":" in u:
        after_at = u.split("@", 1)[1]
        host = after_at.split(":", 1)[0].strip()
        path = after_at.split(":", 1)[1].strip("/")
        parts = [p for p in path.split("/") if p]
        if len(parts) >= 2:
            owner = parts[0]
            repo_name = _strip_dot_git(parts[1])
            return host, owner, repo_name
        return host, None, None

    # Fallback: host/owner/repo.git
    host = u.split("/", 1)[0].strip()
    rest = u.split("/", 1)[1] if "/" in u else ""
    parts = [p for p in rest.strip("/").split("/") if p]
    if len(parts) >= 2:
        owner = parts[0]
        repo_name = _strip_dot_git(parts[1])
        return host, owner, repo_name

    return host, None, None
