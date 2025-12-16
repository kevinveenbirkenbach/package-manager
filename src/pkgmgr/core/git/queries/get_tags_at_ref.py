from __future__ import annotations

from typing import List

from ..errors import GitError
from ..run import run


class GitTagsAtRefQueryError(GitError):
    """Raised when querying tags for a ref fails."""


def get_tags_at_ref(ref: str, *, cwd: str = ".") -> List[str]:
    """
    Return all git tags pointing at a given ref.

    Equivalent to:
      git tag --points-at <ref>
    """
    try:
        output = run(["tag", "--points-at", ref], cwd=cwd)
    except GitError as exc:
        raise GitTagsAtRefQueryError(
            f"Failed to query tags at ref {ref!r}.",
        ) from exc

    if not output:
        return []

    return [line.strip() for line in output.splitlines() if line.strip()]
