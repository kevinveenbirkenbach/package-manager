from __future__ import annotations

import argparse

from .branch_cmd import add_apply_options, add_min_age_option, add_scan_options


def add_worktree_subparsers(subparsers: argparse._SubParsersAction) -> None:
    worktree_parser = subparsers.add_parser(
        "worktree",
        help="Worktree utilities: create, clean up and find abandoned worktrees",
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
    up.add_argument("--json", action="store_true", help="Print the result as JSON")

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
