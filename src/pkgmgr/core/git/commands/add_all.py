# src/pkgmgr/core/git/commands/add_all.py
from __future__ import annotations

from ..errors import GitError, GitCommandError
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
    except GitError as exc:
        raise GitAddAllError("Failed to stage all changes with `git add -A`.", cwd=cwd) from exc
