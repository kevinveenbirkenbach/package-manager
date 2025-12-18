#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse


def add_branch_subparsers(
    subparsers: argparse._SubParsersAction,
) -> None:
    """
    Register branch command and its subcommands.
    """
    branch_parser = subparsers.add_parser(
        "branch",
        help="Branch-related utilities (e.g. open/close/drop feature branches)",
    )
    branch_subparsers = branch_parser.add_subparsers(
        dest="subcommand",
        help="Branch subcommands",
        required=True,
    )

    # -----------------------------------------------------------------------
    # branch open
    # -----------------------------------------------------------------------
    branch_open = branch_subparsers.add_parser(
        "open",
        help="Create and push a new branch on top of a base branch",
    )
    branch_open.add_argument(
        "name",
        nargs="?",
        help=(
            "Name of the new branch (optional; will be asked interactively if omitted)"
        ),
    )
    branch_open.add_argument(
        "--base",
        default="main",
        help="Base branch to create the new branch from (default: main)",
    )

    # -----------------------------------------------------------------------
    # branch close
    # -----------------------------------------------------------------------
    branch_close = branch_subparsers.add_parser(
        "close",
        help="Merge a feature branch into base and delete it",
    )
    branch_close.add_argument(
        "name",
        nargs="?",
        help=(
            "Name of the branch to close (optional; current branch is used if omitted)"
        ),
    )
    branch_close.add_argument(
        "--base",
        default="main",
        help=(
            "Base branch to merge into (default: main; falls back to master "
            "internally if main does not exist)"
        ),
    )
    branch_close.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Skip confirmation prompt and close the branch directly",
    )

    # -----------------------------------------------------------------------
    # branch drop
    # -----------------------------------------------------------------------
    branch_drop = branch_subparsers.add_parser(
        "drop",
        help="Delete a branch locally and on origin (without merging)",
    )
    branch_drop.add_argument(
        "name",
        nargs="?",
        help=(
            "Name of the branch to drop (optional; current branch is used if omitted)"
        ),
    )
    branch_drop.add_argument(
        "--base",
        default="main",
        help=(
            "Base branch used to protect main/master from deletion "
            "(default: main; falls back to master internally)"
        ),
    )
    branch_drop.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Skip confirmation prompt and drop the branch directly",
    )
