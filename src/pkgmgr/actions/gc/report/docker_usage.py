from __future__ import annotations

import json
import subprocess

from pkgmgr.actions.branch.gc import _describe, _docker

DF_ARGS = ["system", "df", "--format", "{{json .}}"]


def _count(value: object) -> int | None:
    text = str(value)
    return int(text) if text.isdigit() else None


def docker_usage() -> tuple[list[dict] | None, str | None]:
    """
    Read `docker system df` per type.

    Returns:
        The rows (type, total and active counts, size and reclaimable as docker
        prints them) and None, or None and a warning when docker is missing,
        fails or prints something else than JSON lines.
    """
    try:
        out = _docker(DF_ARGS)
    except FileNotFoundError:
        return None, "docker unavailable: not installed"
    except subprocess.CalledProcessError as exc:
        return None, f"docker unavailable: {_describe(exc)}"
    rows: list[dict] = []
    for line in out.splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except ValueError:
            data = None
        if not isinstance(data, dict):
            return None, "docker system df: output is not JSON lines"
        rows.append(
            {
                "type": data.get("Type"),
                "total": _count(data.get("TotalCount")),
                "active": _count(data.get("Active")),
                "size": data.get("Size"),
                "reclaimable": data.get("Reclaimable"),
            }
        )
    return rows, None
