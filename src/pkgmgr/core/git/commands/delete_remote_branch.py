from __future__ import annotations

from ..errors import GitRunError, GitCommandError
from ..run import run


class GitDeleteRemoteBranchError(GitCommandError):
    """Raised when deleting a remote branch fails."""


def delete_remote_branch(remote: str, branch: str, cwd: str = ".") -> None:
    try:
        run(["push", remote, "--delete", branch], cwd=cwd)
    except GitRunError as exc:
        raise GitDeleteRemoteBranchError(
            f"Failed to delete remote branch {branch!r} on {remote!r}.",
            cwd=cwd,
        ) from exc
