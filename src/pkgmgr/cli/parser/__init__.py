#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse

from pkgmgr.cli.proxy import register_proxy_commands

from .common import SortedSubParsersAction
from .install_update import add_install_update_subparsers
from .config_cmd import add_config_subparsers
from .navigation_cmd import add_navigation_subparsers
from .branch_cmd import add_branch_subparsers
from .release_cmd import add_release_subparser
from .version_cmd import add_version_subparser
from .changelog_cmd import add_changelog_subparser
from .list_cmd import add_list_subparser
from .make_cmd import add_make_subparsers
from .mirror_cmd import add_mirror_subparsers


def create_parser(description_text: str) -> argparse.ArgumentParser:
    """
    Create the top-level argument parser for pkgmgr.
    """
    parser = argparse.ArgumentParser(
        description=description_text,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(
        dest="command",
        help="Subcommands",
        action=SortedSubParsersAction,
    )

    # Core repo operations
    add_install_update_subparsers(subparsers)
    add_config_subparsers(subparsers)

    # Navigation / tooling around repos
    add_navigation_subparsers(subparsers)

    # Branch & release workflow
    add_branch_subparsers(subparsers)
    add_release_subparser(subparsers)

    # Info commands
    add_version_subparser(subparsers)
    add_changelog_subparser(subparsers)
    add_list_subparser(subparsers)

    # Make wrapper
    add_make_subparsers(subparsers)

    # Mirror management
    add_mirror_subparsers(subparsers)

    # Proxy commands (git, docker, docker compose, ...)
    register_proxy_commands(subparsers)

    return parser


__all__ = [
    "create_parser",
    "SortedSubParsersAction",
]
