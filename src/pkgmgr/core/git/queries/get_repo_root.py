from __future__ import annotations

from ..errors import GitRunError
from ..run import run


def get_repo_root(*, cwd: str = ".") -> str | None:
    """
    Return the git repository root directory (top-level), or None if not available.

    Equivalent to:
      git rev-parse --show-toplevel
    """
    try:
        out = run(["rev-parse", "--show-toplevel"], cwd=cwd)
    except GitRunError:
        return None

    out = out.strip()
    return out or None
