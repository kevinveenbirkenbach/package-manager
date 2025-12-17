from __future__ import annotations

from ..errors import GitRunError, GitCommandError
from ..run import run


class GitAddRemotePushUrlError(GitCommandError):
    """Raised when adding an additional push URL to a remote fails."""


def add_remote_push_url(
    remote: str,
    url: str,
    *,
    cwd: str = ".",
    preview: bool = False,
) -> None:
    """
    Add an additional push URL to a remote.

    Equivalent to:
      git remote set-url --add --push <remote> <url>
    """
    try:
        run(
            ["remote", "set-url", "--add", "--push", remote, url],
            cwd=cwd,
            preview=preview,
        )
    except GitRunError as exc:
        raise GitAddRemotePushUrlError(
            f"Failed to add push url {url!r} to remote {remote!r}.",
            cwd=cwd,
        ) from exc
