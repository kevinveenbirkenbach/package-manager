from __future__ import annotations

import os
import sys

from pkgmgr.actions.branch import (
    branch_gc,
    branch_purge,
    close_branch,
    drop_branch,
    open_branch,
    tree,
)
from pkgmgr.actions.branch.gc import main_repo_root
from pkgmgr.cli.context import CLIContext
from pkgmgr.core.git.errors import GitBaseError
from pkgmgr.core.repository.dir import get_repo_dir


def _known_dirs(ctx: CLIContext) -> list[str]:
    return [
        os.path.expanduser(str(r["directory"]))
        if r.get("directory")
        else get_repo_dir(ctx.repositories_base_dir, r)
        for r in ctx.all_repositories
    ]


def _gc_repo_roots(args, ctx: CLIContext) -> list[str]:
    if not args.all:
        return [main_repo_root(".")]
    return [d for d in _known_dirs(ctx) if os.path.exists(os.path.join(d, ".git"))]


def _refresh(roots: list[str]) -> None:
    for root in roots:
        try:
            tree.refresh_tree_entry(root)
        except (OSError, ValueError, KeyError, GitBaseError) as exc:
            print(f"WARN tree file not rewritten for {root}: {exc}", file=sys.stderr)


def handle_branch(args, ctx: CLIContext) -> None:
    """
    Handle `pkgmgr branch` subcommands.

    Currently supported:
      - pkgmgr branch open  [<name>] [--base <branch>]
      - pkgmgr branch close [<name>] [--base <branch>] [--force|-f]
      - pkgmgr branch drop  [<name>] [--base <branch>] [--force|-f]
      - pkgmgr branch gc    [--apply] [--json] [--all] [--branch N]... [--exclude N]...
                            [--merged-into REF]... [--sizes] [--min-age HOURS]
      - pkgmgr branch purge [--all] [--branch N]... [--exclude N]...
                            [--merged-into REF]... [--sizes] [--min-age HOURS]
      - pkgmgr branch tree  [--format json|yaml] [--output FILE]
    """
    if args.subcommand == "tree":
        sys.exit(
            tree.branch_tree(
                _known_dirs(ctx),
                fmt=args.format,
                output=args.output,
                worktrees_root=tree.WORKTREES_ROOT,
            )
        )

    if args.subcommand in ("gc", "purge"):
        try:
            roots = _gc_repo_roots(args, ctx)
        except GitBaseError as exc:
            print(f"Not inside a git repository: {exc}", file=sys.stderr)
            sys.exit(2)
        options = {
            "include": args.branch,
            "exclude": args.exclude,
            "merged_into": args.merged_into,
            "sizes": args.sizes,
            "min_age": args.min_age,
        }
        if args.subcommand == "gc":
            code = branch_gc(roots, apply=args.apply, as_json=args.json, **options)
        else:
            code = branch_purge(roots, **options)
        if args.subcommand == "purge" or args.apply:
            _refresh(roots)
        sys.exit(code)

    if args.subcommand == "open":
        open_branch(
            name=getattr(args, "name", None),
            base_branch=getattr(args, "base", "main"),
            cwd=".",
        )
        _refresh([main_repo_root(".")])
        return

    if args.subcommand == "close":
        close_branch(
            name=getattr(args, "name", None),
            base_branch=getattr(args, "base", "main"),
            cwd=".",
            force=getattr(args, "force", False),
        )
        _refresh([main_repo_root(".")])
        return

    if args.subcommand == "drop":
        drop_branch(
            name=getattr(args, "name", None),
            base_branch=getattr(args, "base", "main"),
            cwd=".",
            force=getattr(args, "force", False),
        )
        _refresh([main_repo_root(".")])
        return

    print(f"Unknown branch subcommand: {args.subcommand}")
    sys.exit(2)
