from __future__ import annotations

from ..errors import GitRunError
from ..run import run


def get_head_commit(cwd: str = ".") -> str | None:
    """
    Return the current HEAD commit hash, or None if it cannot be determined.
    """
    try:
        output = run(["rev-parse", "HEAD"], cwd=cwd)
    except GitRunError:
        return None
    return output or None
