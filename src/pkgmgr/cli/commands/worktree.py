from __future__ import annotations

import json
import os
import sys

from pkgmgr.actions.branch.gc import main_repo_root
from pkgmgr.actions.gc.report import disk_report, render_text
from pkgmgr.actions.worktree.flow_actions import (
    worktree_flow_clear,
    worktree_flow_set,
    worktree_flow_show,
)
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
FLOW_ACTIONS = ("set", "clear")


def _flow_usage(action: str, args) -> str | None:
    if action == "show" and args.path is not None:
        return f"unknown flow action {args.target!r}; use set or clear"
    if action != "set":
        flags = {
            "--pull": args.pull,
            "--push": args.push,
            "--no-pull": args.no_pull,
            "--no-push": args.no_push,
        }
        used = [flag for flag, value in flags.items() if value]
        return f"{', '.join(used)} only with `flow set`" if used else None
    for kind in ("pull", "push"):
        if bool(getattr(args, kind)) == getattr(args, f"no_{kind}"):
            return f"flow set takes either --{kind} or --no-{kind}"
    return None


def _flow(args) -> int:
    action, path = (
        (args.target, args.path)
        if args.target in FLOW_ACTIONS
        else ("show", args.target)
    )
    problem = _flow_usage(action, args)
    if problem:
        print(f"Refusing: {problem}", file=sys.stderr)
        return 2
    target = path or "."
    if action == "show":
        return worktree_flow_show(target, as_json=args.json)
    if action == "set":
        code = worktree_flow_set(
            target, pull=args.pull or [], push=args.push or [], as_json=args.json
        )
    else:
        code = worktree_flow_clear(target, as_json=args.json)
    if code == 0:
        refresh_tree([main_repo_root(target)])
    return code


def handle_worktree(args, ctx: CLIContext) -> None:
    """
    Handle `pkgmgr worktree` subcommands.

      - pkgmgr worktree up <branch> [--base REF] [--path DIR] [--pull REF ...]
        [--push BRANCH ...] [--json]
      - pkgmgr worktree flow [PATH] [--json]
      - pkgmgr worktree flow set [PATH] (--pull REF ... | --no-pull)
        (--push BRANCH ... | --no-push) [--json]
      - pkgmgr worktree flow clear [PATH] [--json]
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
            pull=args.pull,
            push=args.push,
        )
        refresh_tree([main_repo_root(".")])
        sys.exit(code)

    if args.subcommand == "flow":
        sys.exit(_flow(args))

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
