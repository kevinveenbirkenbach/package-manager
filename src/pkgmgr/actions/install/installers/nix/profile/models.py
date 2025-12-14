from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class NixProfileEntry:
    """
    Minimal normalized representation of one nix profile element entry.
    """

    key: str
    index: Optional[int]
    name: str
    attr_path: str
    store_paths: List[str]
