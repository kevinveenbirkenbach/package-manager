from __future__ import annotations

import json
import os
import sys

from pkgmgr.actions.branch.gc import main_repo_root
from pkgmgr.actions.gc.report import disk_report, render_text
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

MEBIBYTE = 1 << 20


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
    if not args.report:
        run_cleanup(args, ctx, "all")
    if args.apply:
        print(
            "--report only reads; it cannot be combined with --apply", file=sys.stderr
        )
        sys.exit(2)
    report = disk_report(
        [os.path.abspath(os.path.expanduser(root)) for root in args.root],
        scan_repo_roots(args, ctx),
        args.threshold_mb * MEBIBYTE,
        args.docker,
    )
    print(json.dumps(report, indent=2) if args.json else render_text(report))
    sys.exit(0)
