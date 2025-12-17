from __future__ import annotations

from ..errors import GitRunError, GitCommandError
from ..run import run


class GitAddRemoteError(GitCommandError):
    """Raised when adding a remote fails."""


def add_remote(
    name: str,
    url: str,
    *,
    cwd: str = ".",
    preview: bool = False,
) -> None:
    """
    Add a new remote.

    Equivalent to:
      git remote add <name> <url>
    """
    try:
        run(
            ["remote", "add", name, url],
            cwd=cwd,
            preview=preview,
        )
    except GitRunError as exc:
        raise GitAddRemoteError(
            f"Failed to add remote {name!r} with URL {url!r}.",
            cwd=cwd,
        ) from exc
