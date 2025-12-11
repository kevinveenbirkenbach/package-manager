from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class CLIContext:
    """
    Shared runtime context for CLI commands.

    This avoids passing many individual parameters around and
    keeps the CLI layer thin and structured.
    """

    config_merged: Dict[str, Any]
    repositories_base_dir: str
    all_repositories: List[Dict[str, Any]]
    binaries_dir: str
    user_config_path: str
