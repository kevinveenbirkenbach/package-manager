from __future__ import annotations

from ..errors import GitRunError
from ..run import run


def probe_remote_reachable(url: str, cwd: str = ".") -> bool:
    """
    Check whether a remote URL is reachable.

    Equivalent to:
      git ls-remote --exit-code <url>

    Returns:
      True if reachable, False otherwise.
    """
    try:
        run(["ls-remote", "--exit-code", url], cwd=cwd)
        return True
    except GitRunError:
        return False
