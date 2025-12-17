from __future__ import annotations

from ..errors import GitRunError, GitCommandError
from ..run import run


class GitFetchError(GitCommandError):
    """Raised when fetching from a remote fails."""


def fetch(
    remote: str = "origin",
    *,
    prune: bool = False,
    tags: bool = False,
    force: bool = False,
    cwd: str = ".",
    preview: bool = False,
) -> None:
    """
    Fetch from a remote, optionally with prune/tags/force.

    Equivalent to:
      git fetch <remote> [--prune] [--tags] [--force]
    """
    args = ["fetch", remote]
    if prune:
        args.append("--prune")
    if tags:
        args.append("--tags")
    if force:
        args.append("--force")

    try:
        run(args, cwd=cwd, preview=preview)
    except GitRunError as exc:
        raise GitFetchError(
            f"Failed to fetch from remote {remote!r}.",
            cwd=cwd,
        ) from exc
