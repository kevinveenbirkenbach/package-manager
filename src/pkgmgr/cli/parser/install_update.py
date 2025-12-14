#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse

from pkgmgr.cli.parser.common import (
    add_install_update_arguments,
    add_identifier_arguments,
)


def add_install_update_subparsers(
    subparsers: argparse._SubParsersAction,
) -> None:
    """
    Register install / update / deinstall / delete commands.
    """

    install_parser = subparsers.add_parser(
        "install",
        help="Setup repository/repositories alias links to executables",
    )
    add_install_update_arguments(install_parser)
    install_parser.add_argument(
        "--update",
        action="store_true",
        help="Force re-run installers (upgrade/refresh) even if the CLI layer is already loaded",
    )

    update_parser = subparsers.add_parser(
        "update",
        help="Update (pull + install) repository/repositories",
    )
    add_install_update_arguments(update_parser)
    update_parser.add_argument(
        "--system",
        dest="system",
        action="store_true",
        help="Include system update commands",
    )
    # No --update here: update implies force_update=True

    deinstall_parser = subparsers.add_parser(
        "deinstall",
        help="Remove alias links to repository/repositories",
    )
    add_identifier_arguments(deinstall_parser)

    delete_parser = subparsers.add_parser(
        "delete",
        help="Delete repository/repositories alias links to executables",
    )
    add_identifier_arguments(delete_parser)
