from __future__ import annotations

from ..errors import GitRunError, GitCommandError
from ..run import run


class GitPullFfOnlyError(GitCommandError):
    """Raised when pulling with --ff-only fails."""


def pull_ff_only(*, cwd: str = ".", preview: bool = False) -> None:
    """
    Pull using fast-forward only.

    Equivalent to:
      git pull --ff-only
    """
    try:
        run(["pull", "--ff-only"], cwd=cwd, preview=preview)
    except GitRunError as exc:
        raise GitPullFfOnlyError(
            "Failed to pull with --ff-only.",
            cwd=cwd,
        ) from exc
