from __future__ import annotations

from ..errors import GitError, GitCommandError
from ..run import run


class GitDeleteLocalBranchError(GitCommandError):
    """Raised when deleting a local branch fails."""


def delete_local_branch(branch: str, cwd: str = ".", force: bool = False) -> None:
    flag = "-D" if force else "-d"
    try:
        run(["branch", flag, branch], cwd=cwd)
    except GitError as exc:
        raise GitDeleteLocalBranchError(
            f"Failed to delete local branch {branch!r} (flag {flag}).",
            cwd=cwd,
        ) from exc
