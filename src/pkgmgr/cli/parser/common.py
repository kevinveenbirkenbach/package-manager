# src/pkgmgr/cli/parser/common.py
from __future__ import annotations

import argparse
from typing import Optional, Tuple


class SortedSubParsersAction(argparse._SubParsersAction):
    """
    Subparsers action that keeps subcommands sorted alphabetically.
    """

    def add_parser(self, name, **kwargs):
        parser = super().add_parser(name, **kwargs)
        self._choices_actions.sort(key=lambda a: a.dest)
        return parser


def _has_action(
    parser: argparse.ArgumentParser,
    *,
    positional: Optional[str] = None,
    options: Tuple[str, ...] = (),
) -> bool:
    """
    Check whether the parser already has an action.

    - positional: name of a positional argument (e.g. "identifiers")
    - options: option strings (e.g. "--preview", "-q")
    """
    for action in parser._actions:
        if positional and action.dest == positional:
            return True
        if options and any(opt in action.option_strings for opt in options):
            return True
    return False


def _add_positional_if_missing(
    parser: argparse.ArgumentParser,
    name: str,
    **kwargs,
) -> None:
    """Safely add a positional argument."""
    if _has_action(parser, positional=name):
        return
    parser.add_argument(name, **kwargs)


def _add_option_if_missing(
    parser: argparse.ArgumentParser,
    *option_strings: str,
    **kwargs,
) -> None:
    """Safely add an optional argument."""
    if _has_action(parser, options=tuple(option_strings)):
        return
    parser.add_argument(*option_strings, **kwargs)


def add_identifier_arguments(subparser: argparse.ArgumentParser) -> None:
    """
    Common identifier / selection arguments for many subcommands.
    """
    _add_positional_if_missing(
        subparser,
        "identifiers",
        nargs="*",
        help=(
            "Identifier(s) for repositories. "
            "Default: repository of the current working directory."
        ),
    )

    _add_option_if_missing(
        subparser,
        "--all",
        action="store_true",
        default=False,
        help=(
            "Apply the subcommand to all repositories in the config. "
            "Pipe 'yes' to auto-confirm. Example:\n"
            "  yes | pkgmgr <command> --all"
        ),
    )

    _add_option_if_missing(
        subparser,
        "--category",
        nargs="+",
        default=[],
        help="Filter repositories by category (supports /regex/).",
    )

    _add_option_if_missing(
        subparser,
        "--string",
        default="",
        help="Filter repositories by substring or /regex/.",
    )

    _add_option_if_missing(
        subparser,
        "--tag",
        action="append",
        default=[],
        help="Filter repositories by tag (supports /regex/).",
    )

    _add_option_if_missing(
        subparser,
        "--preview",
        action="store_true",
        help="Preview changes without executing commands.",
    )

    _add_option_if_missing(
        subparser,
        "--list",
        action="store_true",
        help="List affected repositories.",
    )

    _add_option_if_missing(
        subparser,
        "-a",
        "--args",
        dest="extra_args",
        nargs=argparse.REMAINDER,
        default=[],
        help="Additional parameters to be attached.",
    )


def add_install_update_arguments(subparser: argparse.ArgumentParser) -> None:
    """
    Common arguments for install/update commands.
    """
    add_identifier_arguments(subparser)

    _add_option_if_missing(
        subparser,
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress warnings and info messages.",
    )

    _add_option_if_missing(
        subparser,
        "--no-verification",
        action="store_true",
        default=False,
        help="Disable verification via commit / GPG.",
    )

    _add_option_if_missing(
        subparser,
        "--dependencies",
        action="store_true",
        help="Also pull and update dependencies.",
    )

    _add_option_if_missing(
        subparser,
        "--clone-mode",
        choices=["ssh", "https", "shallow"],
        default="ssh",
        help="Specify clone mode (default: ssh).",
    )

    _add_option_if_missing(
        subparser,
        "--silent",
        action="store_true",
        help="Continue with other repositories if one fails; downgrade errors to warnings.",
    )
