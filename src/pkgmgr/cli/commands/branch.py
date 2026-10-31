from __future__ import annotations

import os
import sys

from pkgmgr.actions.branch import (
    branch_gc,
    branch_purge,
    close_branch,
    drop_branch,
    open_branch,
)
from pkgmgr.actions.branch.gc import main_repo_root
from pkgmgr.cli.context import CLIContext
from pkgmgr.core.git.errors import GitBaseError
from pkgmgr.core.repository.dir import get_repo_dir


def _gc_repo_roots(args, ctx: CLIContext) -> list[str]:
    if not args.all:
        return [main_repo_root(".")]
    dirs = [get_repo_dir(ctx.repositories_base_dir, r) for r in ctx.all_repositories]
    return [d for d in dirs if os.path.exists(os.path.join(d, ".git"))]


def handle_branch(args, ctx: CLIContext) -> None:
    """
    Handle `pkgmgr branch` subcommands.

    Currently supported:
      - pkgmgr branch open  [<name>] [--base <branch>]
      - pkgmgr branch close [<name>] [--base <branch>] [--force|-f]
      - pkgmgr branch drop  [<name>] [--base <branch>] [--force|-f]
      - pkgmgr branch gc    [--apply] [--json] [--all] [--branch N]... [--exclude N]...
      - pkgmgr branch purge [--all] [--branch N]... [--exclude N]...
    """
    if args.subcommand in ("gc", "purge"):
        try:
            roots = _gc_repo_roots(args, ctx)
        except GitBaseError as exc:
            print(f"Not inside a git repository: {exc}", file=sys.stderr)
            sys.exit(2)
        if args.subcommand == "gc":
            code = branch_gc(
                roots,
                apply=args.apply,
                as_json=args.json,
                include=args.branch,
                exclude=args.exclude,
            )
        else:
            code = branch_purge(roots, include=args.branch, exclude=args.exclude)
        sys.exit(code)

    if args.subcommand == "open":
        open_branch(
            name=getattr(args, "name", None),
            base_branch=getattr(args, "base", "main"),
            cwd=".",
        )
        return

    if args.subcommand == "close":
        close_branch(
            name=getattr(args, "name", None),
            base_branch=getattr(args, "base", "main"),
            cwd=".",
            force=getattr(args, "force", False),
        )
        return

    if args.subcommand == "drop":
        drop_branch(
            name=getattr(args, "name", None),
            base_branch=getattr(args, "base", "main"),
            cwd=".",
            force=getattr(args, "force", False),
        )
        return

    print(f"Unknown branch subcommand: {args.subcommand}")
    sys.exit(2)
