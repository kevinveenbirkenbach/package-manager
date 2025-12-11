#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse

from .common import add_identifier_arguments


def add_config_subparsers(
    subparsers: argparse._SubParsersAction,
) -> None:
    """
    Register config command and its subcommands.
    """
    config_parser = subparsers.add_parser(
        "config",
        help="Manage configuration",
    )
    config_subparsers = config_parser.add_subparsers(
        dest="subcommand",
        help="Config subcommands",
        required=True,
    )

    config_show = config_subparsers.add_parser(
        "show",
        help="Show configuration",
    )
    add_identifier_arguments(config_show)

    config_subparsers.add_parser(
        "add",
        help="Interactively add a new repository entry",
    )

    config_subparsers.add_parser(
        "edit",
        help="Edit configuration file with nano",
    )

    config_subparsers.add_parser(
        "init",
        help="Initialize user configuration by scanning the base directory",
    )

    config_delete = config_subparsers.add_parser(
        "delete",
        help="Delete repository entry from user config",
    )
    add_identifier_arguments(config_delete)

    config_ignore = config_subparsers.add_parser(
        "ignore",
        help="Set ignore flag for repository entries in user config",
    )
    add_identifier_arguments(config_ignore)
    config_ignore.add_argument(
        "--set",
        choices=["true", "false"],
        required=True,
        help="Set ignore to true or false",
    )

    config_subparsers.add_parser(
        "update",
        help=(
            "Update default config files in ~/.config/pkgmgr/ from the "
            "installed pkgmgr package (does not touch config.yaml)."
        ),
    )
