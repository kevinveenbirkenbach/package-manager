from __future__ import annotations

from ..errors import GitRunError, GitCommandError
from ..run import run


class GitSetRemoteUrlError(GitCommandError):
    """Raised when setting a remote URL fails."""


def set_remote_url(
    remote: str,
    url: str,
    *,
    cwd: str = ".",
    push: bool = False,
    preview: bool = False,
) -> None:
    """
    Set the fetch or push URL of a remote.

    Equivalent to:
      git remote set-url <remote> <url>
    or:
      git remote set-url --push <remote> <url>
    """
    args = ["remote", "set-url"]
    if push:
        args.append("--push")
    args += [remote, url]

    try:
        run(
            args,
            cwd=cwd,
            preview=preview,
        )
    except GitRunError as exc:
        mode = "push" if push else "fetch"
        raise GitSetRemoteUrlError(
            f"Failed to set {mode} url for remote {remote!r} to {url!r}.",
            cwd=cwd,
        ) from exc
