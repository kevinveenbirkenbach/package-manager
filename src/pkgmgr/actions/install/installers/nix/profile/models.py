from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NixProfileEntry:
    """
    Minimal normalized representation of one nix profile element entry.
    """

    key: str
    index: int | None
    name: str
    attr_path: str
    store_paths: list[str]
