from __future__ import annotations

from ..errors import GitRunError, GitCommandError
from ..run import run


class GitBranchMoveError(GitCommandError):
    """Raised when renaming/moving a branch fails."""


def branch_move(branch: str, *, cwd: str = ".", preview: bool = False) -> None:
    """
    Rename the current branch to `branch`, creating it if needed.

    Equivalent to:
      git branch -M <branch>
    """
    try:
        run(["branch", "-M", branch], cwd=cwd, preview=preview)
    except GitRunError as exc:
        raise GitBranchMoveError(
            f"Failed to move/rename current branch to {branch!r}.", cwd=cwd
        ) from exc
