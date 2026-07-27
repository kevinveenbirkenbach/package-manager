from __future__ import annotations

from ..errors import GitCommandError, GitRunError
from ..run import run


class GitInitError(GitCommandError):
    """Raised when `git init` fails."""


def init(*, initial_branch: str, cwd: str = ".", preview: bool = False) -> None:
    """
    Initialize a repository with an explicit initial branch.

    Equivalent to:
      git init -b <initial_branch>

    initial_branch: required, so the branch never depends on the ambient
      `init.defaultBranch` git config (which is `master` unless configured).
    """
    try:
        run(["init", "-b", initial_branch], cwd=cwd, preview=preview)
    except GitRunError as exc:
        raise GitInitError("Failed to initialize git repository.", cwd=cwd) from exc
