#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import sys
from typing import Any, Dict, List

from pkgmgr.cli.context import CLIContext
from pkgmgr.actions.install import install_repos
from pkgmgr.actions.repository.deinstall import deinstall_repos
from pkgmgr.actions.repository.delete import delete_repos
from pkgmgr.actions.repository.status import status_repos
from pkgmgr.actions.repository.list import list_repositories
from pkgmgr.actions.repository.create import create_repo
from pkgmgr.core.command.run import run_command
from pkgmgr.core.repository.dir import get_repo_dir

Repository = Dict[str, Any]


def _resolve_repository_directory(repository: Repository, ctx: CLIContext) -> str:
    """
    Resolve the local filesystem directory for a repository.

    Priority:
      1. Use repository["directory"] if present.
      2. Fallback to get_repo_dir(...) using the repositories base directory
         from the CLI context.
    """
    repo_dir = repository.get("directory")
    if repo_dir:
        return repo_dir

    base_dir = getattr(ctx, "repositories_base_dir", None) or getattr(
        ctx, "repositories_dir", None
    )
    if not base_dir:
        raise RuntimeError(
            "Cannot resolve repositories base directory from context; "
            "expected ctx.repositories_base_dir or ctx.repositories_dir."
        )
    return get_repo_dir(base_dir, repository)


def handle_repos_command(
    args,
    ctx: CLIContext,
    selected: List[Repository],
) -> None:
    """
    Handle core repository commands (install/update/deinstall/delete/status/list/path/shell/create).
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
            force_update=getattr(args, "update", False),
            silent=getattr(args, "silent", False),
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
        if not selected:
            print("[pkgmgr] No repositories selected for path.")
            return

        for repository in selected:
            try:
                repo_dir = _resolve_repository_directory(repository, ctx)
            except Exception as exc:
                ident = (
                    f"{repository.get('provider', '?')}/"
                    f"{repository.get('account', '?')}/"
                    f"{repository.get('repository', '?')}"
                )
                print(f"[WARN] Could not resolve directory for {ident}: {exc}")
                continue

            print(repo_dir)
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
            repo_dir = _resolve_repository_directory(repository, ctx)
            print(f"Executing in '{repo_dir}': {command_to_run}")
            run_command(
                command_to_run,
                cwd=repo_dir,
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
