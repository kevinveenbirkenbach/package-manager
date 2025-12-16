from __future__ import annotations

from typing import List

from ..errors import GitError, GitCommandError
from ..run import run


class GitCloneError(GitCommandError):
    """Raised when `git clone` fails."""


def clone(
    args: List[str],
    *,
    cwd: str = ".",
    preview: bool = False,
) -> None:
    """
    Execute `git clone` with caller-provided arguments.

    Examples:
      ["https://example.com/repo.git", "/path/to/dir"]
      ["--depth", "1", "--single-branch", url, dest]
    """
    try:
        run(["clone", *args], cwd=cwd, preview=preview)
    except GitError as exc:
        raise GitCloneError(
            f"Git clone failed with args={args!r}.",
            cwd=cwd,
        ) from exc
