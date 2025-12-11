#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse

from .common import add_identifier_arguments


def add_mirror_subparsers(
    subparsers: argparse._SubParsersAction,
) -> None:
    """
    Register mirror command and its subcommands (list, diff, merge, setup).
    """
    mirror_parser = subparsers.add_parser(
        "mirror",
        help="Mirror-related utilities (list, diff, merge, setup)",
    )
    mirror_subparsers = mirror_parser.add_subparsers(
        dest="subcommand",
        help="Mirror subcommands",
        required=True,
    )

    # ------------------------------------------------------------------
    # mirror list
    # ------------------------------------------------------------------
    mirror_list = mirror_subparsers.add_parser(
        "list",
        help="List configured mirrors for repositories",
    )
    add_identifier_arguments(mirror_list)
    mirror_list.add_argument(
        "--source",
        choices=["all", "config", "file", "resolved"],
        default="all",
        help="Which mirror source to show.",
    )

    # ------------------------------------------------------------------
    # mirror diff
    # ------------------------------------------------------------------
    mirror_diff = mirror_subparsers.add_parser(
        "diff",
        help="Show differences between config mirrors and MIRRORS file",
    )
    add_identifier_arguments(mirror_diff)

    # ------------------------------------------------------------------
    # mirror merge {config,file} {config,file}
    # ------------------------------------------------------------------
    mirror_merge = mirror_subparsers.add_parser(
        "merge",
        help=(
            "Merge mirrors between config and MIRRORS file "
            "(example: pkgmgr mirror merge config file --all)"
        ),
    )

    # First define merge direction positionals, then selection args.
    mirror_merge.add_argument(
        "source",
        choices=["config", "file"],
        help="Source of mirrors.",
    )
    mirror_merge.add_argument(
        "target",
        choices=["config", "file"],
        help="Target of mirrors.",
    )

    # Selection / filter / preview arguments
    add_identifier_arguments(mirror_merge)

    mirror_merge.add_argument(
        "--config-path",
        help=(
            "Path to the user config file to update. "
            "If omitted, the global config path is used."
        ),
    )
    # Note: --preview, --all, --category, --tag, --list, etc. are provided
    # by add_identifier_arguments().

    # ------------------------------------------------------------------
    # mirror setup
    # ------------------------------------------------------------------
    mirror_setup = mirror_subparsers.add_parser(
        "setup",
        help=(
            "Setup mirror configuration for repositories.\n"
            " --local  → configure local Git (remotes, pushurls)\n"
            " --remote → create remote repositories if missing\n"
            "Default: both local and remote."
        ),
    )
    add_identifier_arguments(mirror_setup)
    mirror_setup.add_argument(
        "--local",
        action="store_true",
        help="Only configure the local Git repository.",
    )
    mirror_setup.add_argument(
        "--remote",
        action="store_true",
        help="Only operate on remote repositories.",
    )
    # Note: --preview also comes from add_identifier_arguments().
