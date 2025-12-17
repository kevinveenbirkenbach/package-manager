from __future__ import annotations

from typing import Optional

from ..errors import GitRunError
from ..run import run


def get_upstream_ref(*, cwd: str = ".") -> Optional[str]:
    """
    Return the configured upstream ref for the current branch, or None if none.

    Equivalent to:
      git rev-parse --abbrev-ref --symbolic-full-name @{u}
    """
    try:
        out = run(
            ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
            cwd=cwd,
        )
    except GitRunError:
        return None

    out = out.strip()
    return out or None
