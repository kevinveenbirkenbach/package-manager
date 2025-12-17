from __future__ import annotations

from typing import List

from ..errors import GitRunError, GitCommandError
from ..run import run


class GitPullArgsError(GitCommandError):
    """Raised when `git pull` with arbitrary args fails."""


def pull_args(
    args: List[str] | None = None,
    *,
    cwd: str = ".",
    preview: bool = False,
) -> None:
    """
    Execute `git pull` with caller-provided arguments.

    Examples:
      []                          -> git pull
      ["--ff-only"]               -> git pull --ff-only
      ["--rebase"]                -> git pull --rebase
      ["origin", "main"]          -> git pull origin main
    """
    extra = args or []
    try:
        run(["pull", *extra], cwd=cwd, preview=preview)
    except GitRunError as exc:
        raise GitPullArgsError(
            f"Failed to run `git pull` with args={extra!r}.",
            cwd=cwd,
        ) from exc
