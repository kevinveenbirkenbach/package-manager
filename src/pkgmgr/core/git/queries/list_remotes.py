from __future__ import annotations

from typing import List

from ..run import run


def list_remotes(cwd: str = ".") -> List[str]:
    """
    Return a list of configured git remotes (e.g. ['origin', 'upstream']).

    Raises GitBaseError if the command fails.
    """
    output = run(["remote"], cwd=cwd)
    if not output:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]
