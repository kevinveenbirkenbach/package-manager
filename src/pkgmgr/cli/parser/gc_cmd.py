from __future__ import annotations

import argparse

from .branch_cmd import add_apply_options, add_min_age_option, add_scan_options


def add_gc_subparser(subparsers: argparse._SubParsersAction) -> None:
    gc = subparsers.add_parser(
        "gc",
        help=(
            "Garbage-collect the current repository, or every one with --all: "
            "worktree cleanup and branch cleanup in one pass (dry-run unless --apply)"
        ),
    )
    add_apply_options(gc)
    add_scan_options(gc)
    add_min_age_option(gc)
    gc.add_argument(
        "--report",
        action="store_true",
        help=(
            "Print a read-only disk inventory instead of the cleanup plan: "
            "worktrees, preserved changes, --root children, core dumps, "
            "docker usage and free space per filesystem"
        ),
    )
    gc.add_argument(
        "--root",
        action="append",
        default=[],
        metavar="DIR",
        help="With --report: also measure the direct children of DIR; repeatable",
    )
    gc.add_argument(
        "--threshold-mb",
        type=int,
        default=0,
        metavar="MB",
        help="With --report: list only --root children larger than MB (0: all)",
    )
    gc.add_argument(
        "--docker",
        action="store_true",
        help="With --report: also read `docker system df`",
    )
