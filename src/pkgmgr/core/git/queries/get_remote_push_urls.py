from __future__ import annotations

from typing import Set

from ..run import run


def get_remote_push_urls(remote: str, cwd: str = ".") -> Set[str]:
    """
    Return all push URLs configured for a remote.

    Equivalent to:
      git remote get-url --push --all <remote>

    Raises GitBaseError if the command fails.
    """
    output = run(["remote", "get-url", "--push", "--all", remote], cwd=cwd)
    if not output:
        return set()
    return {line.strip() for line in output.splitlines() if line.strip()}
