from __future__ import annotations

from ..errors import GitRunError, GitCommandError
from ..run import run


class GitPushError(GitCommandError):
    """Raised when pushing to a remote fails."""


def push(
    remote: str,
    ref: str,
    *,
    force: bool = False,
    cwd: str = ".",
    preview: bool = False,
) -> None:
    """
    Push a ref to a remote, optionally forced.

    Equivalent to:
      git push <remote> <ref> [--force]
    """
    args = ["push", remote, ref]
    if force:
        args.append("--force")

    try:
        run(args, cwd=cwd, preview=preview)
    except GitRunError as exc:
        raise GitPushError(
            f"Failed to push ref {ref!r} to remote {remote!r}.",
            cwd=cwd,
        ) from exc
