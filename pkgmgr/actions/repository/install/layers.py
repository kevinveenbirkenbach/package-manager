#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CLI layer model for the pkgmgr installation pipeline.

We treat CLI entry points as coming from one of four conceptual layers:

  - os-packages : system package managers (pacman/apt/dnf/…)
  - nix         : Nix flake / nix profile
  - python      : pip / virtualenv / user-local scripts
  - makefile    : repo-local Makefile / scripts inside the repo

The layer order defines precedence: higher layers "own" the CLI and
lower layers will not be executed once a higher-priority CLI exists.
"""

from __future__ import annotations

import os
from enum import Enum
from typing import Optional


class CliLayer(str, Enum):
    OS_PACKAGES = "os-packages"
    NIX = "nix"
    PYTHON = "python"
    MAKEFILE = "makefile"


# Highest priority first
CLI_LAYERS: list[CliLayer] = [
    CliLayer.OS_PACKAGES,
    CliLayer.NIX,
    CliLayer.PYTHON,
    CliLayer.MAKEFILE,
]


def layer_priority(layer: Optional[CliLayer]) -> int:
    """
    Return a numeric priority index for a given layer.

    Lower index → higher priority.
    Unknown / None → very low priority.
    """
    if layer is None:
        return len(CLI_LAYERS)
    try:
        return CLI_LAYERS.index(layer)
    except ValueError:
        return len(CLI_LAYERS)


def classify_command_layer(command: str, repo_dir: str) -> CliLayer:
    """
    Heuristically classify a resolved command path into a CLI layer.

    Rules (best effort):

      - /usr/... or /bin/...              → os-packages
      - /nix/store/... or ~/.nix-profile → nix
      - ~/.local/bin/...                 → python
      - inside repo_dir                  → makefile
      - everything else                  → python (user/venv scripts, etc.)
    """
    command_abs = os.path.abspath(os.path.expanduser(command))
    repo_abs = os.path.abspath(repo_dir)
    home = os.path.expanduser("~")

    # OS package managers
    if command_abs.startswith("/usr/") or command_abs.startswith("/bin/"):
        return CliLayer.OS_PACKAGES

    # Nix store / profile
    if command_abs.startswith("/nix/store/") or command_abs.startswith(
        os.path.join(home, ".nix-profile")
    ):
        return CliLayer.NIX

    # User-local bin
    if command_abs.startswith(os.path.join(home, ".local", "bin")):
        return CliLayer.PYTHON

    # Inside the repository → usually a Makefile/script
    if command_abs.startswith(repo_abs):
        return CliLayer.MAKEFILE

    # Fallback: treat as Python-style/user-level script
    return CliLayer.PYTHON
