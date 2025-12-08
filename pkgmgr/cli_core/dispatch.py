from __future__ import annotations

import sys
from typing import List

from pkgmgr.cli_core.context import CLIContext
from pkgmgr.cli_core.proxy import maybe_handle_proxy
from pkgmgr.get_selected_repos import get_selected_repos

from pkgmgr.cli_core.commands import (
    handle_repos_command,
    handle_tools_command,
    handle_release,
    handle_version,
    handle_config,
    handle_make,
    handle_changelog,
)


def dispatch_command(args, ctx: CLIContext) -> None:
    """
    Top-level command dispatcher.

    Responsible for:
    - computing selected repositories (where applicable)
    - delegating to the correct command handler module
    """

    # 1) Proxy commands (git, docker, docker compose) short-circuit.
    if maybe_handle_proxy(args, ctx):
        return

    # 2) Determine if this command uses repository selection.
    commands_with_selection: List[str] = [
        "install",
        "update",
        "deinstall",
        "delete",
        "status",
        "path",
        "shell",
        "code",
        "explore",
        "terminal",
        "release",
        "version",
        "make",
        "changelog",
    ]

    if args.command in commands_with_selection:
        selected = get_selected_repos(
            getattr(args, "all", False),
            ctx.all_repositories,
            getattr(args, "identifiers", []),
        )
    else:
        selected = []

    # 3) Delegate based on command.
    if args.command in (
        "install",
        "update",
        "deinstall",
        "delete",
        "status",
        "path",
        "shell",
        "create",
        "list",
    ):
        handle_repos_command(args, ctx, selected)
    elif args.command in ("code", "explore", "terminal"):
        handle_tools_command(args, ctx, selected)
    elif args.command == "release":
        handle_release(args, ctx, selected)
    elif args.command == "version":
        handle_version(args, ctx, selected)
    elif args.command == "changelog":
        handle_changelog(args, ctx, selected)
    elif args.command == "config":
        handle_config(args, ctx)
    elif args.command == "make":
        handle_make(args, ctx, selected)
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(2)
