from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

Repository = Dict[str, Any]
MirrorMap = Dict[str, str]


@dataclass(frozen=True)
class RepoMirrorContext:
    """
    Bundle mirror-related information for a single repository.
    """

    identifier: str
    repo_dir: str
    config_mirrors: MirrorMap
    file_mirrors: MirrorMap

    @property
    def resolved_mirrors(self) -> MirrorMap:
        """
        Combined mirrors from config and MIRRORS file.

        Strategy:
          - Start from config mirrors
          - Overlay MIRRORS file (file wins on same name)
        """
        merged: MirrorMap = dict(self.config_mirrors)
        merged.update(self.file_mirrors)
        return merged
