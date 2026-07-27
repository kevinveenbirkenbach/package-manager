from __future__ import annotations

from ..run import run


def list_tags(pattern: str = "*", *, cwd: str = ".") -> list[str]:
    """
    List tags matching a pattern.

    Equivalent to:
      git tag --list <pattern>
    """
    out = run(["tag", "--list", pattern], cwd=cwd)
    if not out:
        return []
    return [line.strip() for line in out.splitlines() if line.strip()]
