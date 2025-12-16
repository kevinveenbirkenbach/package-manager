from __future__ import annotations

from ..errors import GitError, GitCommandError
from ..run import run


class GitPushError(GitCommandError):
    """Raised when pushing to a remote fails."""


def push(remote: str, ref: str, cwd: str = ".") -> None:
    try:
        run(["push", remote, ref], cwd=cwd)
    except GitError as exc:
        raise GitPushError(
            f"Failed to push ref {ref!r} to remote {remote!r}.",
            cwd=cwd,
        ) from exc
