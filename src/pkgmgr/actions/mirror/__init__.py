"""
High-level mirror actions.

Public API:
    - list_mirrors
    - diff_mirrors
    - merge_mirrors
    - setup_mirrors
"""

from __future__ import annotations

from .diff_cmd import diff_mirrors
from .list_cmd import list_mirrors
from .merge_cmd import merge_mirrors
from .setup_cmd import setup_mirrors
from .types import MirrorMap, Repository
from .visibility_cmd import set_mirror_visibility

__all__ = [
    "MirrorMap",
    "Repository",
    "diff_mirrors",
    "list_mirrors",
    "merge_mirrors",
    "set_mirror_visibility",
    "setup_mirrors",
]
