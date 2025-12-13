# src/pkgmgr/actions/install/context.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Shared context object for repository installation steps.

This data class bundles all information needed by installer components so
they do not depend on global state or long parameter lists.
"""

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class RepoContext:
    """Container for all repository-related data used during installation."""

    repo: Dict[str, Any]
    identifier: str
    repo_dir: str
    repositories_base_dir: str
    bin_dir: str
    all_repos: List[Dict[str, Any]]

    no_verification: bool
    preview: bool
    quiet: bool
    clone_mode: str
    update_dependencies: bool

    # If True, allow re-running installers of the currently active layer.
    force_update: bool = False
