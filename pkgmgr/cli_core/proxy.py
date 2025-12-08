#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import sys
from typing import Dict, List

from pkgmgr.cli_core.context import CLIContext
from pkgmgr.clone_repos import clone_repos
from pkgmgr.exec_proxy_command import exec_proxy_command
from pkgmgr.pull_with_verification import pull_with_verification
from pkgmgr.get_selected_repos import get_selected_repos


PROXY_COMMANDS: Dict[str, List[str]] = {
    "git": [
        "pull",
        "push",
        "diff",
        "add",
        "show",
        "checkout",
        "clone",
        "reset",
        "revert",
        "rebase",
        "commit",
    ],
    "docker": [
        "start",
        "stop",
        "build",
    ],
    "docker compose": [
        "up",
        "down",
        "exec",
        "ps",
        "restart",
    ],
}


def _add_proxy_identifier_arguments(parser: argparse.ArgumentParser) -> None:
    """
    Selection arguments for proxy subcommands.
    """
    parser.add_argument(
        "identifiers",
        nargs="*",
        help=(
            "Identifier(s) for repositories. "
            "Default: Repository of current folder."
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        default=False,
        help=(
            "Apply the subcommand to all repositories in the config. "
            "Some subcommands ask for confirmation. If you want to give this "
            "confirmation for all repositories, pipe 'yes'. E.g: "
            "yes | pkgmgr {subcommand} --all"
        ),
    )
    parser.add_argument(
        "--category",
        nargs="+",
        default=[],
        help=(
            "Filter repositories by category patterns derived from config "
            "filenames or repo metadata (use filename without .yml/.yaml, "
            "or /regex/ to use a regular expression)."
        ),
    )
    parser.add_argument(
        "--string",
        default="",
        help=(
            "Filter repositories whose identifier / name / path contains this "
            "substring (case-insensitive). Use /regex/ for regular expressions."
        ),
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview changes without executing commands",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List affected repositories (with preview or status)",
    )
    parser.add_argument(
        "-a",
        "--args",
        nargs=argparse.REMAINDER,
        dest="extra_args",
        help="Additional parameters to be attached.",
        default=[],
    )


def register_proxy_commands(
    subparsers: argparse._SubParsersAction,
) -> None:
    """
    Register proxy subcommands for git, docker, docker compose, ...
    """
    for command, subcommands in PROXY_COMMANDS.items():
        for subcommand in subcommands:
            parser = subparsers.add_parser(
                subcommand,
                help=f"Proxies '{command} {subcommand}' to repository/ies",
                description=(
                    f"Executes '{command} {subcommand}' for the "
                    "selected repositories. "
                    "For more details see the underlying tool's help: "
                    f"'{command} {subcommand} --help'"
                ),
                formatter_class=argparse.RawTextHelpFormatter,
            )

            if subcommand in ["pull", "clone"]:
                parser.add_argument(
                    "--no-verification",
                    action="store_true",
                    default=False,
                    help="Disable verification via commit/gpg",
                )
            if subcommand == "clone":
                parser.add_argument(
                    "--clone-mode",
                    choices=["ssh", "https", "shallow"],
                    default="ssh",
                    help=(
                        "Specify the clone mode: ssh, https, or shallow "
                        "(HTTPS shallow clone; default: ssh)"
                    ),
                )

            _add_proxy_identifier_arguments(parser)


def maybe_handle_proxy(args: argparse.Namespace, ctx: CLIContext) -> bool:
    """
    If the top-level command is one of the proxy subcommands
    (git / docker / docker compose), handle it here and return True.
    """
    all_proxy_subcommands = {
        sub for subs in PROXY_COMMANDS.values() for sub in subs
    }

    if args.command not in all_proxy_subcommands:
        return False

    selected = get_selected_repos(args, ctx.all_repositories)

    for command, subcommands in PROXY_COMMANDS.items():
        if args.command not in subcommands:
            continue

        if args.command == "clone":
            clone_repos(
                selected,
                ctx.repositories_base_dir,
                ctx.all_repositories,
                args.preview,
                args.no_verification,
                args.clone_mode,
            )
        elif args.command == "pull":
            pull_with_verification(
                selected,
                ctx.repositories_base_dir,
                ctx.all_repositories,
                args.extra_args,
                args.no_verification,
                args.preview,
            )
        else:
            exec_proxy_command(
                command,
                selected,
                ctx.repositories_base_dir,
                ctx.all_repositories,
                args.command,
                args.extra_args,
                args.preview,
            )

        sys.exit(0)

    return True