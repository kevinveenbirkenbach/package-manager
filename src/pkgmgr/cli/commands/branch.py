from __future__ import annotations

import sys

from pkgmgr.cli.context import CLIContext
from pkgmgr.actions.branch import open_branch, close_branch, drop_branch


def handle_branch(args, ctx: CLIContext) -> None:
    """
    Handle `pkgmgr branch` subcommands.

    Currently supported:
      - pkgmgr branch open  [<name>] [--base <branch>]
      - pkgmgr branch close [<name>] [--base <branch>] [--force|-f]
      - pkgmgr branch drop  [<name>] [--base <branch>] [--force|-f]
    """
    if args.subcommand == "open":
        open_branch(
            name=getattr(args, "name", None),
            base_branch=getattr(args, "base", "main"),
            cwd=".",
        )
        return

    if args.subcommand == "close":
        close_branch(
            name=getattr(args, "name", None),
            base_branch=getattr(args, "base", "main"),
            cwd=".",
            force=getattr(args, "force", False),
        )
        return

    if args.subcommand == "drop":
        drop_branch(
            name=getattr(args, "name", None),
            base_branch=getattr(args, "base", "main"),
            cwd=".",
            force=getattr(args, "force", False),
        )
        return

    print(f"Unknown branch subcommand: {args.subcommand}")
    sys.exit(2)
