from __future__ import annotations

from typing import List

from ..errors import GitRunError
from ..run import run


def get_tags(cwd: str = ".") -> List[str]:
    """
    Return a list of all tags in the repository in `cwd`.

    If there are no tags, an empty list is returned.
    """
    try:
        output = run(["tag"], cwd=cwd)
    except GitRunError as exc:
        # If the repo is not a git repo, surface a clear error.
        if "not a git repository" in str(exc):
            raise
        return []

    if not output:
        return []

    return [line.strip() for line in output.splitlines() if line.strip()]
