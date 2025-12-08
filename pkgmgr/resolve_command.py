#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Command resolver for repositories.

This module determines the correct command to expose via symlink.
It implements the following priority:

1. Explicit command in repo config                 → command
2. System package manager binary (/usr/...)        → NO LINK (respect OS)
3. Nix profile binary (~/.nix-profile/bin/<id>)    → command
4. Python / non-system console script on PATH      → command
5. Fallback: repository's main.sh or main.py       → command
6. If nothing is available                         → raise error

The actual symlink creation is handled by create_ink(). This resolver
only decides *what* should be used as the entrypoint, or whether no
link should be created at all.
"""

import os
import shutil
from typing import Optional


def resolve_command_for_repo(repo, repo_identifier: str, repo_dir: str) -> Optional[str]:
    """
    Determine the command for this repository.

    Returns:
        str  → path to the command (a symlink should be created)
        None → do NOT create a link (e.g. system package already provides it)

    On total failure (no suitable command found at any layer), this function
    raises SystemExit with a descriptive error message.
    """
    # ------------------------------------------------------------
    # 1. Explicit command defined by repository config
    # ------------------------------------------------------------
    explicit = repo.get("command")
    if explicit:
        return explicit

    home = os.path.expanduser("~")

    def is_executable(path: str) -> bool:
        return os.path.exists(path) and os.access(path, os.X_OK)

    # ------------------------------------------------------------
    # 2. System package manager binary via PATH
    #
    #    If the binary lives under /usr/, we treat it as a system-managed
    #    package (e.g. installed via pacman/apt/yum). In that case, pkgmgr
    #    does NOT create a link at all and defers entirely to the OS.
    # ------------------------------------------------------------
    path_candidate = shutil.which(repo_identifier)
    system_binary: Optional[str] = None
    non_system_binary: Optional[str] = None

    if path_candidate:
        if path_candidate.startswith("/usr/"):
            system_binary = path_candidate
        else:
            non_system_binary = path_candidate

    if system_binary:
        # Respect system package manager: do not create a link.
        if repo.get("debug", False):
            print(
                f"[pkgmgr] System binary for '{repo_identifier}' found at "
                f"{system_binary}; no symlink will be created."
            )
        return None

    # ------------------------------------------------------------
    # 3. Nix profile binary (~/.nix-profile/bin/<identifier>)
    # ------------------------------------------------------------
    nix_candidate = os.path.join(home, ".nix-profile", "bin", repo_identifier)
    if is_executable(nix_candidate):
        return nix_candidate

    # ------------------------------------------------------------
    # 4. Python / non-system console script on PATH
    #
    #    Here we reuse the non-system PATH candidate (e.g. from a venv or
    #    a user-local install like ~/.local/bin). This is treated as a
    #    valid command target.
    # ------------------------------------------------------------
    if non_system_binary and is_executable(non_system_binary):
        return non_system_binary

    # ------------------------------------------------------------
    # 5. Fallback: main.sh / main.py inside the repository
    # ------------------------------------------------------------
    main_sh = os.path.join(repo_dir, "main.sh")
    main_py = os.path.join(repo_dir, "main.py")

    if is_executable(main_sh):
        return main_sh

    if is_executable(main_py) or os.path.exists(main_py):
        return main_py

    # ------------------------------------------------------------
    # 6. Nothing found → treat as a hard error
    # ------------------------------------------------------------
    raise SystemExit(
        f"No executable command could be resolved for repository '{repo_identifier}'. "
        "No explicit 'command' configured, no system-managed binary under /usr/, "
        "no Nix profile binary, no non-system console script on PATH, and no "
        "main.sh/main.py found in the repository."
    )
