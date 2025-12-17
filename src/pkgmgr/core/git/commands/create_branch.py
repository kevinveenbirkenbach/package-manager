from __future__ import annotations

from ..errors import GitRunError, GitCommandError
from ..run import run


class GitCreateBranchError(GitCommandError):
    """Raised when creating a new branch fails."""


def create_branch(branch: str, base: str, cwd: str = ".") -> None:
    """
    Create a new branch from a base branch.

    Equivalent to: git checkout -b <branch> <base>
    """
    try:
        run(["checkout", "-b", branch, base], cwd=cwd)
    except GitRunError as exc:
        raise GitCreateBranchError(
            f"Failed to create branch {branch!r} from base {base!r}.",
            cwd=cwd,
        ) from exc
