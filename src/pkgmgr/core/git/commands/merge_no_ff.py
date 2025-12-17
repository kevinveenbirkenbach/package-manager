from __future__ import annotations

from ..errors import GitRunError, GitCommandError
from ..run import run


class GitMergeError(GitCommandError):
    """Raised when merging a branch fails."""


def merge_no_ff(branch: str, cwd: str = ".") -> None:
    try:
        run(["merge", "--no-ff", branch], cwd=cwd)
    except GitRunError as exc:
        raise GitMergeError(
            f"Failed to merge branch {branch!r} with --no-ff.",
            cwd=cwd,
        ) from exc
