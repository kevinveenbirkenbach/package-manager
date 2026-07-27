from __future__ import annotations

from ..errors import GitRunError
from ..run import run


def get_current_branch(cwd: str = ".") -> str | None:
    """
    Return the current branch name, or None if it cannot be determined.

    Note: In detached HEAD state this will return 'HEAD'.
    """
    try:
        output = run(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    except GitRunError:
        return None
    return output or None
