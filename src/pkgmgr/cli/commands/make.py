from __future__ import annotations

import sys
from typing import Any

from pkgmgr.actions.proxy import exec_proxy_command
from pkgmgr.cli.context import CLIContext

Repository = dict[str, Any]


def handle_make(
    args,
    ctx: CLIContext,
    selected: list[Repository],
) -> None:
    """
    Handle the 'make' command by delegating to exec_proxy_command.

    This mirrors the old behaviour where `make` was treated as a
    special proxy command.
    """
    exec_proxy_command(
        "make",
        selected,
        ctx.repositories_base_dir,
        ctx.all_repositories,
        args.subcommand,
        getattr(args, "extra_args", []),
        getattr(args, "preview", False),
    )
    sys.exit(0)
