from __future__ import annotations

import sys

from pkgmgr.cli_core.context import CLIContext
from pkgmgr.branch_commands import open_branch


def handle_branch(args, ctx: CLIContext) -> None:
    """
    Handle `pkgmgr branch` subcommands.

    Currently supported:
      - pkgmgr branch open [<name>] [--base <branch>]
    """
    if args.subcommand == "open":
        open_branch(
            name=getattr(args, "name", None),
            base_branch=getattr(args, "base", "main"),
            cwd=".",
        )
        return

    print(f"Unknown branch subcommand: {args.subcommand}")
    sys.exit(2)
