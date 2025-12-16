# src/pkgmgr/core/git/commands/init.py
from __future__ import annotations

from ..errors import GitError, GitCommandError
from ..run import run


class GitInitError(GitCommandError):
    """Raised when `git init` fails."""


def init(*, cwd: str = ".", preview: bool = False) -> None:
    """
    Initialize a repository.

    Equivalent to:
      git init
    """
    try:
        run(["init"], cwd=cwd, preview=preview)
    except GitError as exc:
        raise GitInitError("Failed to initialize git repository.", cwd=cwd) from exc
