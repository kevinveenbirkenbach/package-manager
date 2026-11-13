from __future__ import annotations

import os
import sys

from pkgmgr.actions.branch import (
    branch_purge,
    cleanup,
    close_branch,
    drop_branch,
    open_branch,
    tree,
)
from pkgmgr.actions.branch.gc import local_repo_root, main_repo_root
from pkgmgr.cli.context import CLIContext
from pkgmgr.core.git.errors import GitBaseError
from pkgmgr.core.repository.dir import get_repo_dir


def _repo_dir(ctx: CLIContext, repo: dict) -> str:
    return (
        os.path.expanduser(str(repo["directory"]))
        if repo.get("directory")
        else get_repo_dir(ctx.repositories_base_dir, repo)
    )


def _known_dirs(ctx: CLIContext) -> list[str]:
    return [_repo_dir(ctx, r) for r in ctx.all_repositories]


def pinned_hooks(ctx: CLIContext) -> dict[str, dict[str, list[str]]]:
    """
    Bind the `worktree_hooks` config to managed repositories, never to a
    remote URL, which the repository's own config sets.

    Args:
        ctx: CLI context; each `worktree_hooks` key names the
            `<provider>/<account>/<repository>` of a `repositories` entry.

    Returns:
        Realpath of each pinned managed repository's directory -> hook name
        -> argv; keys that match no managed repository are dropped.
    """
    pins = ctx.config_merged["worktree_hooks"]
    return {
        os.path.realpath(_repo_dir(ctx, repo)): pins[key]
        for repo in ctx.config_merged["repositories"]
        if all(repo.get(part) for part in ("provider", "account", "repository"))
        and (key := f"{repo['provider']}/{repo['account']}/{repo['repository']}")
        in pins
    }


def refresh_tree(roots: list[str]) -> None:
    for root in roots:
        try:
            tree.refresh_tree_entry(root)
        except (OSError, ValueError, KeyError, GitBaseError) as exc:
            print(f"WARN tree file not rewritten for {root}: {exc}", file=sys.stderr)


def scan_repo_roots(args, ctx: CLIContext, local: bool = False) -> list[str]:
    """
    Resolve the repositories a scan covers: the current one, or every
    pkgmgr-managed one with --all. Exits with 2 outside a repository.

    Args:
        args: parsed arguments; `all` selects every managed repository.
        ctx: CLI context.
        local: resolve the current repository as scope `local` does, also in
            a submodule or with a separate git dir, refusing a mismatch.

    Returns:
        The main worktree roots to scan.
    """
    if not args.all:
        try:
            return [(local_repo_root if local else main_repo_root)(".")]
        except GitBaseError as exc:
            print(f"Not inside a git repository: {exc}", file=sys.stderr)
            sys.exit(2)
    return [d for d in _known_dirs(ctx) if os.path.exists(os.path.join(d, ".git"))]


def scan_options(args) -> dict:
    return {
        "include": args.branch,
        "exclude": args.exclude,
        "merged_into": args.merged_into,
        "sizes": args.sizes,
    }


def run_cleanup(args, ctx: CLIContext, scope: str) -> None:
    roots = scan_repo_roots(args, ctx, local=scope == "local")
    code = cleanup(
        roots,
        scope=scope,
        apply=args.apply,
        as_json=args.json,
        min_age=args.min_age,
        hooks=pinned_hooks(ctx),
        **scan_options(args),
    )
    if args.apply and scope != "local":
        refresh_tree(roots)
    sys.exit(code)


def handle_branch(args, ctx: CLIContext) -> None:
    """
    Handle `pkgmgr branch` subcommands.

    Currently supported:
      - pkgmgr branch open    [<name>] [--base <branch>]
      - pkgmgr branch close   [<name>] [--base <branch>] [--force|-f]
      - pkgmgr branch drop    [<name>] [--base <branch>] [--force|-f]
      - pkgmgr branch cleanup [--apply] [--json] [--local] [--all] [--branch N]...
                              [--exclude N]... [--merged-into REF]... [--sizes]
                              [--min-age HOURS]
      - pkgmgr branch purge   [--all] [--branch N]... [--exclude N]...
                              [--merged-into REF]... [--sizes] [--min-age HOURS]
      - pkgmgr branch tree    [--format json|yaml] [--output FILE]
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

    if args.subcommand == "cleanup":
        run_cleanup(args, ctx, "local" if args.local else "branch")

    if args.subcommand == "purge":
        roots = scan_repo_roots(args, ctx)
        code = branch_purge(
            roots,
            min_age=args.min_age,
            hooks=pinned_hooks(ctx),
            **scan_options(args),
        )
        refresh_tree(roots)
        sys.exit(code)

    if args.subcommand == "open":
        open_branch(
            name=getattr(args, "name", None),
            base_branch=getattr(args, "base", "main"),
            cwd=".",
        )
        refresh_tree([main_repo_root(".")])
        return

    if args.subcommand == "close":
        close_branch(
            name=getattr(args, "name", None),
            base_branch=getattr(args, "base", "main"),
            cwd=".",
            force=getattr(args, "force", False),
        )
        refresh_tree([main_repo_root(".")])
        return

    if args.subcommand == "drop":
        drop_branch(
            name=getattr(args, "name", None),
            base_branch=getattr(args, "base", "main"),
            cwd=".",
            force=getattr(args, "force", False),
        )
        refresh_tree([main_repo_root(".")])
        return

    print(f"Unknown branch subcommand: {args.subcommand}")
    sys.exit(2)
