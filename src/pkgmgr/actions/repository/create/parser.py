from __future__ import annotations

import re
from typing import Tuple
from urllib.parse import urlparse

from .model import RepoParts

_NAME_RE = re.compile(r"^[a-z0-9_-]+$")


def parse_identifier(identifier: str) -> RepoParts:
    ident = identifier.strip()

    if "://" in ident or ident.startswith("git@"):
        return _parse_git_url(ident)

    parts = ident.split("/")
    if len(parts) != 3:
        raise ValueError("Identifier must be URL or 'provider(:port)/owner/repo'.")

    host_with_port, owner, name = parts
    host, port = _split_host_port(host_with_port)
    _ensure_valid_repo_name(name)

    return RepoParts(host=host, port=port, owner=owner, name=name)


def _parse_git_url(url: str) -> RepoParts:
    if url.startswith("git@") and "://" not in url:
        left, right = url.split(":", 1)
        host = left.split("@", 1)[1]
        owner, name = right.lstrip("/").split("/", 1)
        name = _strip_git_suffix(name)
        _ensure_valid_repo_name(name)
        return RepoParts(host=host, port=None, owner=owner, name=name)

    parsed = urlparse(url)
    host = parsed.hostname or ""
    port = str(parsed.port) if parsed.port else None
    path = (parsed.path or "").strip("/")

    if not host or "/" not in path:
        raise ValueError(f"Could not parse git URL: {url}")

    owner, name = path.split("/", 1)
    name = _strip_git_suffix(name)
    _ensure_valid_repo_name(name)

    return RepoParts(host=host, port=port, owner=owner, name=name)


def _split_host_port(host: str) -> Tuple[str, str | None]:
    if ":" in host:
        h, p = host.split(":", 1)
        return h, p or None
    return host, None


def _strip_git_suffix(name: str) -> str:
    return name[:-4] if name.endswith(".git") else name


def _ensure_valid_repo_name(name: str) -> None:
    if not _NAME_RE.fullmatch(name):
        raise ValueError("Repository name must match: lowercase a-z, 0-9, '_' and '-'.")
