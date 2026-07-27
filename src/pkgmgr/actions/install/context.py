# src/pkgmgr/actions/install/context.py

"""
Shared context object for repository installation steps.

This data class bundles all information needed by installer components so
they do not depend on global state or long parameter lists.
"""

from dataclasses import dataclass
from typing import Any


@dataclass
class RepoContext:
    """Container for all repository-related data used during installation."""

    repo: dict[str, Any]
    identifier: str
    repo_dir: str
    repositories_base_dir: str
    bin_dir: str
    all_repos: list[dict[str, Any]]

    no_verification: bool
    preview: bool
    quiet: bool
    clone_mode: str
    update_dependencies: bool

    # If True, allow re-running installers of the currently active layer.
    force_update: bool = False
