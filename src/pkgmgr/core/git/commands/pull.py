from __future__ import annotations

from ..errors import GitError, GitCommandError
from ..run import run


class GitPullError(GitCommandError):
    """Raised when pulling from a remote branch fails."""


def pull(remote: str, branch: str, cwd: str = ".") -> None:
    try:
        run(["pull", remote, branch], cwd=cwd)
    except GitError as exc:
        raise GitPullError(
            f"Failed to pull {remote!r}/{branch!r}.",
            cwd=cwd,
        ) from exc
