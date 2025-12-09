#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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
    handle_version,
    handle_config,
    handle_make,
    handle_changelog,
    handle_branch,
)


def _has_explicit_selection(args) -> bool:
    """
    Return True if the user explicitly selected repositories via
    identifiers / --all / --category / --tag / --string.
    """
    identifiers = getattr(args, "identifiers", []) or []
    use_all = getattr(args, "all", False)
    categories = getattr(args, "category", []) or []
    tags = getattr(args, "tag", []) or []
    string_filter = getattr(args, "string", "") or ""

    return bool(
        use_all
        or identifiers
        or categories
        or tags
        or string_filter
    )


def _select_repo_for_current_directory(
    ctx: CLIContext,
) -> List[Dict[str, Any]]:
    """
    Heuristic: find the repository whose local directory matches the
    current working directory or is the closest parent.

    Example:
      - Repo directory: /home/kevin/Repositories/foo
      - CWD:           /home/kevin/Repositories/foo/subdir
      → 'foo' is selected.
    """
    cwd = os.path.abspath(os.getcwd())
    candidates: List[tuple[str, Dict[str, Any]]] = []

    for repo in ctx.all_repositories:
        repo_dir = repo.get("directory")
        if not repo_dir:
            try:
                repo_dir = get_repo_dir(ctx.repositories_base_dir, repo)
            except Exception:
                repo_dir = None
        if not repo_dir:
            continue

        repo_dir_abs = os.path.abspath(os.path.expanduser(repo_dir))
        if cwd == repo_dir_abs or cwd.startswith(repo_dir_abs + os.sep):
            candidates.append((repo_dir_abs, repo))

    if not candidates:
        return []

    # Pick the repo with the longest (most specific) path.
    candidates.sort(key=lambda item: len(item[0]), reverse=True)
    return [candidates[0][1]]


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
        if _has_explicit_selection(args):
            # Classic selection logic (identifiers / --all / filters)
            selected = get_selected_repos(args, ctx.all_repositories)
        else:
            # Default per help text: repository of current folder.
            selected = _select_repo_for_current_directory(ctx)
            # If none is found, leave 'selected' empty.
            # Individual handlers will then emit a clear message instead
            # of silently picking an unrelated repository.
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
