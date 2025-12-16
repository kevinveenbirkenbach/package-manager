from __future__ import annotations

from ..errors import GitError, GitCommandError
from ..run import run


class GitFetchError(GitCommandError):
    """Raised when fetching from a remote fails."""


def fetch(remote: str = "origin", cwd: str = ".") -> None:
    try:
        run(["fetch", remote], cwd=cwd)
    except GitError as exc:
        raise GitFetchError(
            f"Failed to fetch from remote {remote!r}.",
            cwd=cwd,
        ) from exc
