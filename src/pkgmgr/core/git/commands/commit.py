from __future__ import annotations

from ..errors import GitError, GitCommandError
from ..run import run


class GitCommitError(GitCommandError):
    """Raised when `git commit` fails."""


def commit(
    message: str,
    *,
    cwd: str = ".",
    all: bool = False,
    preview: bool = False,
) -> None:
    """
    Create a commit.

    Equivalent to:
      git commit -m "<message>"
    or (if all=True):
      git commit -am "<message>"
    """
    args = ["commit"]
    if all:
        args.append("-a")
    args += ["-m", message]

    try:
        run(args, cwd=cwd, preview=preview)
    except GitError as exc:
        raise GitCommitError(
            "Failed to create commit.",
            cwd=cwd,
        ) from exc
