from __future__ import annotations

import os
import sys
from typing import List, Dict, Any

from pkgmgr.cli.context import CLIContext
from pkgmgr.cli.proxy import maybe_handle_proxy
from pkgmgr.core.repository.selected import get_selected_repos
from pkgmgr.core.repository.dir import get_repo_dir

from pkgmgr.cli.commands import (
    handle_repos_command,
    handle_tools_command,
    handle_release,
    handle_publish,
    handle_version,
    handle_config,
    handle_make,
    handle_changelog,
    handle_branch,
    handle_mirror_command,
)


def _has_explicit_selection(args) -> bool:
    return bool(
        getattr(args, "all", False)
        or getattr(args, "identifiers", [])
        or getattr(args, "category", [])
        or getattr(args, "tag", [])
        or getattr(args, "string", "")
    )


def _select_repo_for_current_directory(ctx: CLIContext) -> List[Dict[str, Any]]:
    cwd = os.path.abspath(os.getcwd())
    matches = []

    for repo in ctx.all_repositories:
        repo_dir = repo.get("directory")
        if not repo_dir:
            try:
                repo_dir = get_repo_dir(ctx.repositories_base_dir, repo)
            except Exception:
                continue

        repo_dir = os.path.abspath(os.path.expanduser(repo_dir))
        if cwd == repo_dir or cwd.startswith(repo_dir + os.sep):
            matches.append((repo_dir, repo))

    if not matches:
        return []

    matches.sort(key=lambda x: len(x[0]), reverse=True)
    return [matches[0][1]]


def dispatch_command(args, ctx: CLIContext) -> None:
    if maybe_handle_proxy(args, ctx):
        return

    commands_with_selection = {
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
        "publish",
        "version",
        "changelog",
        "explore",
        "terminal",
        "code",
        "mirror",
    }

    if args.command in commands_with_selection:
        selected = (
            get_selected_repos(args, ctx.all_repositories)
            if _has_explicit_selection(args)
            else _select_repo_for_current_directory(ctx)
        )
    else:
        selected = []

    if args.command in {
        "install",
        "deinstall",
        "delete",
        "status",
        "path",
        "shell",
        "create",
        "list",
    }:
        handle_repos_command(args, ctx, selected)
        return

    if args.command == "update":
        from pkgmgr.actions.update import UpdateManager

        UpdateManager().run(
            selected_repos=selected,
            repositories_base_dir=ctx.repositories_base_dir,
            bin_dir=ctx.binaries_dir,
            all_repos=ctx.all_repositories,
            no_verification=args.no_verification,
            system_update=args.system,
            preview=args.preview,
            quiet=args.quiet,
            update_dependencies=args.dependencies,
            clone_mode=args.clone_mode,
            silent=getattr(args, "silent", False),
            force_update=True,
        )
        return

    if args.command in ("explore", "terminal", "code"):
        handle_tools_command(args, ctx, selected)
        return

    if args.command == "release":
        handle_release(args, ctx, selected)
        return

    if args.command == "publish":
        handle_publish(args, ctx, selected)
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

    if args.command == "mirror":
        handle_mirror_command(ctx, args, selected)
        return

    print(f"Unknown command: {args.command}")
    sys.exit(2)
