from __future__ import annotations

import sys
from typing import Any, Dict, List

from pkgmgr.cli.context import CLIContext
from pkgmgr.actions.proxy import exec_proxy_command


Repository = Dict[str, Any]


def handle_make(
    args,
    ctx: CLIContext,
    selected: List[Repository],
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
