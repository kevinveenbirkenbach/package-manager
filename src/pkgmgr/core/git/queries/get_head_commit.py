from __future__ import annotations

from typing import Optional

from ..errors import GitError
from ..run import run


def get_head_commit(cwd: str = ".") -> Optional[str]:
    """
    Return the current HEAD commit hash, or None if it cannot be determined.
    """
    try:
        output = run(["rev-parse", "HEAD"], cwd=cwd)
    except GitError:
        return None
    return output or None
