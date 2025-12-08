#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import sys
from typing import Any, Dict, List

from pkgmgr.cli_core.context import CLIContext
from pkgmgr.install_repos import install_repos
from pkgmgr.deinstall_repos import deinstall_repos
from pkgmgr.delete_repos import delete_repos
from pkgmgr.update_repos import update_repos
from pkgmgr.status_repos import status_repos
from pkgmgr.list_repositories import list_repositories
from pkgmgr.run_command import run_command
from pkgmgr.create_repo import create_repo
from pkgmgr.get_selected_repos import get_selected_repos

Repository = Dict[str, Any]


def handle_repos_command(
    args,
    ctx: CLIContext,
    selected: List[Repository],
) -> None:
    """
    Handle core repository commands (install/update/deinstall/delete/.../list).
    """

    # ------------------------------------------------------------
    # install
    # ------------------------------------------------------------
    if args.command == "install":
        install_repos(
            selected,
            ctx.repositories_base_dir,
            ctx.binaries_dir,
            ctx.all_repositories,
            args.no_verification,
            args.preview,
            args.quiet,
            args.clone_mode,
            args.dependencies,
        )
        return

    # ------------------------------------------------------------
    # update
    # ------------------------------------------------------------
    if args.command == "update":
        update_repos(
            selected,
            ctx.repositories_base_dir,
            ctx.binaries_dir,
            ctx.all_repositories,
            args.no_verification,
            args.system,
            args.preview,
            args.quiet,
            args.dependencies,
            args.clone_mode,
        )
        return

    # ------------------------------------------------------------
    # deinstall
    # ------------------------------------------------------------
    if args.command == "deinstall":
        deinstall_repos(
            selected,
            ctx.repositories_base_dir,
            ctx.binaries_dir,
            ctx.all_repositories,
            preview=args.preview,
        )
        return

    # ------------------------------------------------------------
    # delete
    # ------------------------------------------------------------
    if args.command == "delete":
        delete_repos(
            selected,
            ctx.repositories_base_dir,
            ctx.all_repositories,
            preview=args.preview,
        )
        return

    # ------------------------------------------------------------
    # status
    # ------------------------------------------------------------
    if args.command == "status":
        status_repos(
            selected,
            ctx.repositories_base_dir,
            ctx.all_repositories,
            args.extra_args,
            list_only=args.list,
            system_status=args.system,
            preview=args.preview,
        )
        return

    # ------------------------------------------------------------
    # path
    # ------------------------------------------------------------
    if args.command == "path":
        for repository in selected:
            print(repository["directory"])
        return

    # ------------------------------------------------------------
    # shell
    # ------------------------------------------------------------
    if args.command == "shell":
        if not args.shell_command:
            print("[ERROR] 'shell' requires a command via -c/--command.")
            sys.exit(2)
        command_to_run = " ".join(args.shell_command)
        for repository in selected:
            print(
                f"Executing in '{repository['directory']}': {command_to_run}"
            )
            run_command(
                command_to_run,
                cwd=repository["directory"],
                preview=args.preview,
            )
        return

    # ------------------------------------------------------------
    # create
    # ------------------------------------------------------------
    if args.command == "create":
        if not args.identifiers:
            print(
                "[ERROR] 'create' requires at least one identifier "
                "in the format provider/account/repository."
            )
            sys.exit(1)

        for identifier in args.identifiers:
            create_repo(
                identifier,
                ctx.config_merged,
                ctx.user_config_path,
                ctx.binaries_dir,
                remote=args.remote,
                preview=args.preview,
            )
        return

    # ------------------------------------------------------------
    # list
    # ------------------------------------------------------------
    if args.command == "list":
        list_repositories(
            selected,
            ctx.repositories_base_dir,
            ctx.binaries_dir,
            status_filter=getattr(args, "status", "") or "",
            extra_tags=getattr(args, "tag", []) or [],
            show_description=getattr(args, "description", False),
        )
        return

    print(f"[ERROR] Unknown repos command: {args.command}")
    sys.exit(2)
