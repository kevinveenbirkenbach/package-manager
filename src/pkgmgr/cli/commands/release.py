#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import sys
from typing import Any, Dict, List

from pkgmgr.actions.publish import publish as run_publish
from pkgmgr.actions.release import release as run_release
from pkgmgr.cli.context import CLIContext
from pkgmgr.core.repository.dir import get_repo_dir
from pkgmgr.core.repository.identifier import get_repo_identifier

Repository = Dict[str, Any]


def handle_release(
    args,
    ctx: CLIContext,
    selected: List[Repository],
) -> None:
    if not selected:
        print("[pkgmgr] No repositories selected for release.")
        return

    if getattr(args, "list", False):
        print("[pkgmgr] Repositories that would be affected by this release:")
        for repo in selected:
            identifier = get_repo_identifier(repo, ctx.all_repositories)
            print(f"  - {identifier}")
        return

    for repo in selected:
        identifier = get_repo_identifier(repo, ctx.all_repositories)

        try:
            repo_dir = repo.get("directory") or get_repo_dir(
                ctx.repositories_base_dir, repo
            )
        except Exception as exc:
            print(
                f"[WARN] Skipping repository {identifier}: failed to resolve directory: {exc}"
            )
            continue

        if not os.path.isdir(repo_dir):
            print(f"[WARN] Skipping repository {identifier}: directory missing.")
            continue

        print(f"[pkgmgr] Running release for repository {identifier}...")

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

            if not getattr(args, "no_publish", False):
                print(f"[pkgmgr] Running publish for repository {identifier}...")
                is_tty = sys.stdin.isatty()
                run_publish(
                    repo=repo,
                    repo_dir=repo_dir,
                    preview=getattr(args, "preview", False),
                    interactive=is_tty,
                    allow_prompt=is_tty,
                )

        finally:
            os.chdir(cwd_before)
