#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse

from .common import add_identifier_arguments


def add_mirror_subparsers(subparsers: argparse._SubParsersAction) -> None:
    mirror_parser = subparsers.add_parser(
        "mirror",
        help="Mirror-related utilities (list, diff, merge, setup, check, provision, visibility)",
    )
    mirror_subparsers = mirror_parser.add_subparsers(
        dest="subcommand",
        metavar="SUBCOMMAND",
        required=True,
    )

    mirror_list = mirror_subparsers.add_parser(
        "list", help="List configured mirrors for repositories"
    )
    add_identifier_arguments(mirror_list)
    mirror_list.add_argument(
        "--source",
        choices=["config", "file", "all"],
        default="all",
        help="Which mirror source to show.",
    )

    mirror_diff = mirror_subparsers.add_parser(
        "diff", help="Show differences between config mirrors and MIRRORS file"
    )
    add_identifier_arguments(mirror_diff)

    mirror_merge = mirror_subparsers.add_parser(
        "merge",
        help="Merge mirrors between config and MIRRORS file (example: pkgmgr mirror merge config file --all)",
    )
    mirror_merge.add_argument(
        "source", choices=["config", "file"], help="Source of mirrors."
    )
    mirror_merge.add_argument(
        "target", choices=["config", "file"], help="Target of mirrors."
    )
    add_identifier_arguments(mirror_merge)
    mirror_merge.add_argument(
        "--config-path",
        help="Path to the user config file to update. If omitted, the global config path is used.",
    )

    mirror_setup = mirror_subparsers.add_parser(
        "setup",
        help="Configure local Git remotes and push URLs (origin, pushurl list).",
    )
    add_identifier_arguments(mirror_setup)

    mirror_check = mirror_subparsers.add_parser(
        "check",
        help="Check remote mirror reachability (git ls-remote). Read-only.",
    )
    add_identifier_arguments(mirror_check)

    mirror_provision = mirror_subparsers.add_parser(
        "provision",
        help="Provision remote repositories via provider APIs (create missing repos).",
    )
    mirror_provision.add_argument(
        "--public",
        action="store_true",
        help="After ensuring repos exist, enforce public visibility on the remote provider.",
    )
    add_identifier_arguments(mirror_provision)

    mirror_visibility = mirror_subparsers.add_parser(
        "visibility",
        help="Set visibility (public/private) for all remote git mirrors via provider APIs.",
    )
    mirror_visibility.add_argument(
        "visibility",
        choices=["private", "public"],
        help="Target visibility for all git mirrors.",
    )
    add_identifier_arguments(mirror_visibility)
