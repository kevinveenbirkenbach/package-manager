from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CLIContext:
    """
    Shared runtime context for CLI commands.

    This avoids passing many individual parameters around and
    keeps the CLI layer thin and structured.
    """

    config_merged: dict[str, Any]
    repositories_base_dir: str
    all_repositories: list[dict[str, Any]]
    binaries_dir: str
    user_config_path: str
