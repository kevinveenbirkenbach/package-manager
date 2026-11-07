from __future__ import annotations

import argparse

from .branch_cmd import add_apply_options, add_min_age_option, add_scan_options


def _add_flow_options(parser: argparse.ArgumentParser, default: str) -> None:
    parser.add_argument(
        "--pull",
        action="append",
        metavar="REF",
        help=(
            "Ref merged into the branch before a gate, deploy or merge; "
            f"repeatable, kept in order ({default})"
        ),
    )
    parser.add_argument(
        "--push",
        action="append",
        metavar="BRANCH",
        help=(
            "Branch the branch is merged into when finished, then pushed by "
            f"the operator; repeatable, kept in order ({default})"
        ),
    )


def _add_flow_parser(worktree_subparsers: argparse._SubParsersAction) -> None:
    flow = worktree_subparsers.add_parser(
        "flow",
        help=(
            "Show, set or clear the worktree's merge flow in "
            "<git-dir>/pkgmgr/flow.yml: pull refs merged in, push branches "
            "merged into"
        ),
    )
    flow.add_argument(
        "target",
        nargs="?",
        metavar="set|clear|PATH",
        help="`set` or `clear`, else the worktree to show (default: .)",
    )
    flow.add_argument(
        "path",
        nargs="?",
        metavar="PATH",
        help="Worktree of set or clear (default: .)",
    )
    _add_flow_options(flow, "set only, replaces the list")
    flow.add_argument(
        "--no-pull", action="store_true", help="set only: an empty pull list"
    )
    flow.add_argument(
        "--no-push", action="store_true", help="set only: an empty push list"
    )
    flow.add_argument("--json", action="store_true", help="Print the flow as JSON")


def add_worktree_subparsers(subparsers: argparse._SubParsersAction) -> None:
    worktree_parser = subparsers.add_parser(
        "worktree",
        help=(
            "Worktree utilities: create, keep a merge flow, clean up and find "
            "abandoned worktrees"
        ),
    )
    worktree_subparsers = worktree_parser.add_subparsers(
        dest="subcommand",
        help="Worktree subcommands",
        required=True,
    )

    up = worktree_subparsers.add_parser(
        "up",
        help=(
            "Check a branch out under <directories.worktrees>/<host>/<owner>/"
            "<repo>/<branch>, assign a slot and run `make worktree-init SLOT=<n>` "
            "when the project defines it"
        ),
    )
    up.add_argument("name", help="Branch to check out; created when it exists nowhere")
    up.add_argument(
        "--base",
        metavar="REF",
        help="Start point of a new branch (origin's default branch when omitted)",
    )
    up.add_argument(
        "--path",
        metavar="DIR",
        help=(
            "Exact checkout path instead of the standard one, e.g. a directory "
            "an agent sandbox releases"
        ),
    )
    _add_flow_options(up, "default: the base, for push its local branch")
    up.add_argument("--json", action="store_true", help="Print the result as JSON")

    _add_flow_parser(worktree_subparsers)

    cleanup = worktree_subparsers.add_parser(
        "cleanup",
        help=(
            "Remove clean worktrees whose commits are merged or pushed: "
            "`make worktree-fini`, compose stack, checkout; the branch stays "
            "(dry-run unless --apply)"
        ),
    )
    add_apply_options(cleanup)
    add_scan_options(cleanup)
    add_min_age_option(cleanup)

    orphans = worktree_subparsers.add_parser(
        "orphans",
        help="List merged and abandoned branches and worktrees with a proposal each",
    )
    add_scan_options(orphans)
    orphans.add_argument(
        "--stale-days",
        type=int,
        required=True,
        metavar="DAYS",
        help="Unfinished work idle for longer counts as stale-open",
    )
    orphans.add_argument(
        "--top",
        type=int,
        required=True,
        metavar="N",
        help="Rows per class in the text table; 0 prints the counts only",
    )
    orphans.add_argument("--json", action="store_true", help="Print every row as JSON")
