from __future__ import annotations

import sys

from pkgmgr.actions.branch.gc import main_repo_root
from pkgmgr.actions.worktree.orphans import worktree_orphans
from pkgmgr.actions.worktree.up import worktree_up
from pkgmgr.cli.context import CLIContext

from .branch import (
    pinned_hooks,
    refresh_tree,
    run_cleanup,
    scan_options,
    scan_repo_roots,
)


def handle_worktree(args, ctx: CLIContext) -> None:
    """
    Handle `pkgmgr worktree` subcommands.

      - pkgmgr worktree up <branch> [--base REF] [--path DIR] [--json]
      - pkgmgr worktree cleanup [--apply] [--json] [scan options] [--min-age HOURS]
      - pkgmgr worktree orphans --stale-days N --top N [--json] [scan options]
    """
    if args.subcommand == "up":
        code = worktree_up(
            ".",
            args.name,
            base=args.base,
            worktrees_dir=ctx.config_merged["directories"]["worktrees"],
            path=args.path,
            hooks=pinned_hooks(ctx),
            as_json=args.json,
        )
        refresh_tree([main_repo_root(".")])
        sys.exit(code)

    if args.subcommand == "cleanup":
        run_cleanup(args, ctx, "worktree")

    if args.subcommand == "orphans":
        sys.exit(
            worktree_orphans(
                scan_repo_roots(args, ctx),
                stale_days=args.stale_days,
                top=args.top,
                as_json=args.json,
                **scan_options(args),
            )
        )

    print(f"Unknown worktree subcommand: {args.subcommand}")
    sys.exit(2)


def handle_gc(args, ctx: CLIContext) -> None:
    run_cleanup(args, ctx, "all")
