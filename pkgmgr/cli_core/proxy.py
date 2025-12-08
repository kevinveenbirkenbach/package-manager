from __future__ import annotations

import argparse
import sys
from typing import Dict, List

from pkgmgr.cli_core.context import CLIContext
from pkgmgr.clone_repos import clone_repos
from pkgmgr.exec_proxy_command import exec_proxy_command
from pkgmgr.get_selected_repos import get_selected_repos
from pkgmgr.pull_with_verification import pull_with_verification


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
    Local copy of the identifier argument set for proxy commands.

    This duplicates the semantics of cli.parser.add_identifier_arguments
    to avoid circular imports.
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
    Register proxy commands (git, docker, docker compose) as
    top-level subcommands on the given subparsers.
    """
    for command, subcommands in PROXY_COMMANDS.items():
        for subcommand in subcommands:
            parser = subparsers.add_parser(
                subcommand,
                help=f"Proxies '{command} {subcommand}' to repository/ies",
                description=(
                    f"Executes '{command} {subcommand}' for the "
                    "identified repos.\nTo recieve more help execute "
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
    If the parsed command is a proxy command, execute it and return True.
    Otherwise return False to let the main dispatcher continue.
    """
    all_proxy_subcommands = {
        sub for subs in PROXY_COMMANDS.values() for sub in subs
    }

    if args.command not in all_proxy_subcommands:
        return False

    # Use generic selection semantics for proxies
    selected = get_selected_repos(
        getattr(args, "all", False),
        ctx.all_repositories,
        getattr(args, "identifiers", []),
    )

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
