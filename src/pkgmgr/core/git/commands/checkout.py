from __future__ import annotations

from ..errors import GitRunError, GitCommandError
from ..run import run


class GitCheckoutError(GitCommandError):
    """Raised when checking out a branch fails."""


def checkout(branch: str, cwd: str = ".") -> None:
    try:
        run(["checkout", branch], cwd=cwd)
    except GitRunError as exc:
        raise GitCheckoutError(
            f"Failed to checkout branch {branch!r}.",
            cwd=cwd,
        ) from exc
