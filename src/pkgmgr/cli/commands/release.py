#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Release command wiring for the pkgmgr CLI.

This module implements the `pkgmgr release` subcommand on top of the
generic selection logic from cli.dispatch. It does not define its
own subparser; the CLI surface is configured in cli.parser.

Responsibilities:
  - Take the parsed argparse.Namespace for the `release` command.
  - Use the list of selected repositories provided by dispatch_command().
  - Optionally list affected repositories when --list is set.
  - For each selected repository, run pkgmgr.actions.release.release(...) in
    the context of that repository directory.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

from pkgmgr.cli.context import CLIContext
from pkgmgr.core.repository.dir import get_repo_dir
from pkgmgr.core.repository.identifier import get_repo_identifier
from pkgmgr.actions.release import release as run_release


Repository = Dict[str, Any]


def handle_release(
    args,
    ctx: CLIContext,
    selected: List[Repository],
) -> None:
    """
    Handle the `pkgmgr release` subcommand.

    Flow:
      1) Use the `selected` repositories as computed by dispatch_command().
      2) If --list is given, print the identifiers of the selected repos
         and return without running any release.
      3) For each selected repository:
           - Resolve its identifier and local directory.
           - Change into that directory.
           - Call pkgmgr.actions.release.release(...) with the parsed options.
    """
    if not selected:
        print("[pkgmgr] No repositories selected for release.")
        return

    # List-only mode: show which repositories would be affected.
    if getattr(args, "list", False):
        print("[pkgmgr] Repositories that would be affected by this release:")
        for repo in selected:
            identifier = get_repo_identifier(repo, ctx.all_repositories)
            print(f"  - {identifier}")
        return

    for repo in selected:
        identifier = get_repo_identifier(repo, ctx.all_repositories)

        repo_dir = repo.get("directory")
        if not repo_dir:
            try:
                repo_dir = get_repo_dir(ctx.repositories_base_dir, repo)
            except Exception:
                repo_dir = None

        if not repo_dir or not os.path.isdir(repo_dir):
            print(
                f"[WARN] Skipping repository {identifier}: "
                "local directory does not exist."
            )
            continue

        print(
            f"[pkgmgr] Running release for repository {identifier} "
            f"in '{repo_dir}'..."
        )

        # Change to repo directory and invoke the helper.
        cwd_before = os.getcwd()
        try:
            os.chdir(repo_dir)
            run_release(
                pyproject_path="pyproject.toml",
                changelog_path="CHANGELOG.md",
                release_type=args.release_type,
                message=args.message or None,
                preview=getattr(args, "preview", False),
                force=getattr(args, "force", False),
                close=getattr(args, "close", False),
            )
        finally:
            os.chdir(cwd_before)
