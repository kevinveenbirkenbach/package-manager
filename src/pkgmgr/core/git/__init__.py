from __future__ import annotations

from .errors import GitRunError
from .run import run

"""
Lightweight helper functions around Git commands.

These helpers are intentionally small wrappers so that higher-level
logic (release, version, changelog) does not have to deal with the
details of subprocess handling.
"""

__all__ = [
    "GitRunError",
    "run",
]
