# src/pkgmgr/core/git/commands/push_upstream.py
from __future__ import annotations

from ..errors import GitError, GitCommandError
from ..run import run


class GitPushUpstreamError(GitCommandError):
    """Raised when pushing a branch with upstream tracking fails."""


def push_upstream(
    remote: str,
    branch: str,
    *,
    cwd: str = ".",
    preview: bool = False,
) -> None:
    """
    Push a branch and set upstream tracking.

    Equivalent to:
      git push -u <remote> <branch>
    """
    try:
        run(["push", "-u", remote, branch], cwd=cwd, preview=preview)
    except GitError as exc:
        raise GitPushUpstreamError(
            f"Failed to push branch {branch!r} to {remote!r} with upstream tracking.",
            cwd=cwd,
        ) from exc
