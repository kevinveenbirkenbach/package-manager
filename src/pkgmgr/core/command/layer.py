# src/pkgmgr/core/command/layer.py
from __future__ import annotations

from enum import Enum


class CliLayer(str, Enum):
    """
    CLI layer precedence (lower number = stronger layer).
    """

    OS_PACKAGES = "os-packages"
    NIX = "nix"
    PYTHON = "python"
    MAKEFILE = "makefile"


_LAYER_PRIORITY: dict[CliLayer, int] = {
    CliLayer.OS_PACKAGES: 0,
    CliLayer.NIX: 1,
    CliLayer.PYTHON: 2,
    CliLayer.MAKEFILE: 3,
}


def layer_priority(layer: CliLayer) -> int:
    """
    Return precedence priority for the given layer.
    Lower value means higher priority (stronger layer).
    """
    return _LAYER_PRIORITY.get(layer, 999)
