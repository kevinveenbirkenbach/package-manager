from __future__ import annotations

from ..errors import GitCommandError, GitRunError
from ..run import run


class GitAddAllError(GitCommandError):
    """Raised when `git add -A` fails."""


def add_all(*, cwd: str = ".", preview: bool = False) -> None:
    """
    Stage all changes (tracked + untracked).

    Equivalent to:
      git add -A
    """
    try:
        run(["add", "-A"], cwd=cwd, preview=preview)
    except GitRunError as exc:
        raise GitAddAllError(
            "Failed to stage all changes with `git add -A`.", cwd=cwd
        ) from exc
