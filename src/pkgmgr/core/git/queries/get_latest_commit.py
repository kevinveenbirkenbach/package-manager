from __future__ import annotations

from typing import Optional

from ..errors import GitRunError
from ..run import run


def get_latest_commit(cwd: str = ".") -> Optional[str]:
    """
    Return the latest commit hash for the repository in `cwd`.

    Equivalent to:
      git log -1 --format=%H

    Returns:
      The commit hash string, or None if it cannot be determined
      (e.g. not a git repo, no commits, or other git failure).
    """
    try:
        output = run(["log", "-1", "--format=%H"], cwd=cwd)
    except GitRunError:
        return None

    output = output.strip()
    return output or None
