from __future__ import annotations

from ..errors import GitCommandError, GitRunError
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
      git push [--force] -- <remote> <ref>
    """
    args = ["push", *(["--force"] if force else []), "--", remote, ref]

    try:
        run(args, cwd=cwd, preview=preview)
    except GitRunError as exc:
        raise GitPushError(
            f"Failed to push ref {ref!r} to remote {remote!r}.",
            cwd=cwd,
        ) from exc
