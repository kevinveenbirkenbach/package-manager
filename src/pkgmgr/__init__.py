#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Top-level pkgmgr package.

We deliberately avoid importing heavy submodules (like the CLI)
on import to keep unit tests fast and to not require optional
dependencies (like PyYAML) unless they are actually used.

Accessing ``pkgmgr.cli`` will load the CLI module lazily via
``__getattr__``. This keeps patterns like

    from pkgmgr import cli

working as expected in tests and entry points.
"""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = ["cli"]


def __getattr__(name: str) -> Any:
    """
    Lazily expose ``pkgmgr.cli`` as attribute on the top-level package.

    This keeps ``import pkgmgr`` lightweight while still allowing
    ``from pkgmgr import cli`` in tests and entry points.
    """
    if name == "cli":
        return import_module("pkgmgr.cli")
    raise AttributeError(f"module 'pkgmgr' has no attribute {name!r}")
