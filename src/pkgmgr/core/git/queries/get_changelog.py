from __future__ import annotations

from typing import Optional

from ..errors import GitQueryError, GitRunError
from ..run import run


class GitChangelogQueryError(GitQueryError):
    """Raised when querying the git changelog fails."""


def get_changelog(
    *,
    cwd: str,
    from_ref: Optional[str] = None,
    to_ref: Optional[str] = None,
    include_merges: bool = False,
) -> str:
    """
    Return a plain-text changelog between two Git refs.

    Uses:
      git log --pretty=format:%h %d %s [--no-merges] <range>

    Raises:
      GitChangelogQueryError on failure.
    """
    if to_ref is None:
        to_ref = "HEAD"

    rev_range = f"{from_ref}..{to_ref}" if from_ref else to_ref

    cmd = ["log", "--pretty=format:%h %d %s"]
    if not include_merges:
        cmd.append("--no-merges")
    cmd.append(rev_range)

    try:
        return run(cmd, cwd=cwd)
    except GitRunError as exc:
        raise GitChangelogQueryError(
            f"Failed to query changelog for range {rev_range!r}.",
        ) from exc
