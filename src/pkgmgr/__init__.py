from __future__ import annotations

"""
Top-level package for Kevin's package manager (pkgmgr).

We re-export the CLI subpackage as the attribute ``cli`` so that
``pkgutil.resolve_name("pkgmgr.cli.commands.release")`` and similar
lookups work reliably under Python 3.13+.
"""

# Re-export the CLI subpackage as an attribute on the package.
from . import cli as cli  # type: ignore[F401]

__all__ = ["cli"]
