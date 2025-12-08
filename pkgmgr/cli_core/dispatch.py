#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
    handle_branch,
)


def dispatch_command(args, ctx: CLIContext) -> None:
    """
    Dispatch the parsed arguments to the appropriate command handler.
    """

    # First: proxy commands (git / docker / docker compose / make wrapper etc.)
    if maybe_handle_proxy(args, ctx):
        return

    # Commands that operate on repository selections
    commands_with_selection: List[str] = [
        "install",
        "update",
        "deinstall",
        "delete",
        "status",
        "path",
        "shell",
        "create",
        "list",
        "make",
        "release",
        "version",
        "changelog",
        "explore",
        "terminal",
        "code",
    ]

    if getattr(args, "command", None) in commands_with_selection:
        selected = get_selected_repos(args, ctx.all_repositories)
    else:
        selected = []

    # ------------------------------------------------------------------ #
    # Repos-related commands
    # ------------------------------------------------------------------ #
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
        return

    # ------------------------------------------------------------------ #
    # Tools (explore / terminal / code)
    # ------------------------------------------------------------------ #
    if args.command in ("explore", "terminal", "code"):
        handle_tools_command(args, ctx, selected)
        return

    # ------------------------------------------------------------------ #
    # Release / Version / Changelog / Config / Make / Branch
    # ------------------------------------------------------------------ #
    if args.command == "release":
        handle_release(args, ctx, selected)
        return

    if args.command == "version":
        handle_version(args, ctx, selected)
        return

    if args.command == "changelog":
        handle_changelog(args, ctx, selected)
        return

    if args.command == "config":
        handle_config(args, ctx)
        return

    if args.command == "make":
        handle_make(args, ctx, selected)
        return

    if args.command == "branch":
        handle_branch(args, ctx)
        return

    print(f"Unknown command: {args.command}")
    sys.exit(2)
