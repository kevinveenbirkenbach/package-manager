from __future__ import annotations

from urllib.parse import urlparse

from .types import PyPITarget


def parse_pypi_project_url(url: str) -> PyPITarget | None:
    u = (url or "").strip()
    if not u:
        return None

    parsed = urlparse(u)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").strip("/")

    if host not in ("pypi.org", "test.pypi.org"):
        return None

    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2 and parts[0] == "project":
        return PyPITarget(host=host, project=parts[1])

    return None
