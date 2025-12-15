from __future__ import annotations

import argparse

from pkgmgr.cli.proxy import register_proxy_commands

from .branch_cmd import add_branch_subparsers
from .changelog_cmd import add_changelog_subparser
from .common import SortedSubParsersAction
from .config_cmd import add_config_subparsers
from .install_update import add_install_update_subparsers
from .list_cmd import add_list_subparser
from .make_cmd import add_make_subparsers
from .mirror_cmd import add_mirror_subparsers
from .navigation_cmd import add_navigation_subparsers
from .publish_cmd import add_publish_subparser
from .release_cmd import add_release_subparser
from .version_cmd import add_version_subparser


def create_parser(description_text: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=description_text,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    subparsers = parser.add_subparsers(
        dest="command",
        help="Subcommands",
        action=SortedSubParsersAction,
    )

    # create
    p_create = subparsers.add_parser(
        "create",
        help="Create a new repository (scaffold + config).",
    )
    p_create.add_argument(
        "identifiers",
        nargs="+",
        help="Repository identifier(s): URL or 'provider(:port)/owner/repo'.",
    )
    p_create.add_argument(
        "--remote",
        action="store_true",
        help="Also push an initial commit to the remote (main/master).",
    )
    p_create.add_argument(
        "--preview",
        action="store_true",
        help="Print actions without writing files or executing commands.",
    )

    add_install_update_subparsers(subparsers)
    add_config_subparsers(subparsers)
    add_navigation_subparsers(subparsers)

    add_branch_subparsers(subparsers)
    add_release_subparser(subparsers)
    add_publish_subparser(subparsers)

    add_version_subparser(subparsers)
    add_changelog_subparser(subparsers)
    add_list_subparser(subparsers)

    add_make_subparsers(subparsers)
    add_mirror_subparsers(subparsers)

    register_proxy_commands(subparsers)
    return parser


__all__ = ["create_parser", "SortedSubParsersAction"]
