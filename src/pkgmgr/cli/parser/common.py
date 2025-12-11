#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse


class SortedSubParsersAction(argparse._SubParsersAction):
    """
    Subparsers action that keeps choices sorted alphabetically.
    """

    def add_parser(self, name, **kwargs):
        parser = super().add_parser(name, **kwargs)
        # Sort choices alphabetically by dest (subcommand name)
        self._choices_actions.sort(key=lambda a: a.dest)
        return parser


def add_identifier_arguments(subparser: argparse.ArgumentParser) -> None:
    """
    Common identifier / selection arguments for many subcommands.

    Selection modes (mutual intent, not hard-enforced):
      - identifiers (positional): select by alias / provider/account/repo
      - --all: select all repositories
      - --category / --string / --tag: filter-based selection on top
        of the full repository set
    """
    subparser.add_argument(
        "identifiers",
        nargs="*",
        help=(
            "Identifier(s) for repositories. "
            "Default: Repository of current folder."
        ),
    )
    subparser.add_argument(
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
    subparser.add_argument(
        "--category",
        nargs="+",
        default=[],
        help=(
            "Filter repositories by category patterns derived from config "
            "filenames or repo metadata (use filename without .yml/.yaml, "
            "or /regex/ to use a regular expression)."
        ),
    )
    subparser.add_argument(
        "--string",
        default="",
        help=(
            "Filter repositories whose identifier / name / path contains this "
            "substring (case-insensitive). Use /regex/ for regular expressions."
        ),
    )
    subparser.add_argument(
        "--tag",
        action="append",
        default=[],
        help=(
            "Filter repositories by tag. Matches tags from the repository "
            "collector and category tags. Use /regex/ for regular expressions."
        ),
    )
    subparser.add_argument(
        "--preview",
        action="store_true",
        help="Preview changes without executing commands",
    )
    subparser.add_argument(
        "--list",
        action="store_true",
        help="List affected repositories (with preview or status)",
    )
    subparser.add_argument(
        "-a",
        "--args",
        nargs=argparse.REMAINDER,
        dest="extra_args",
        help="Additional parameters to be attached.",
        default=[],
    )


def add_install_update_arguments(subparser: argparse.ArgumentParser) -> None:
    """
    Common arguments for install/update commands.
    """
    add_identifier_arguments(subparser)
    subparser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress warnings and info messages",
    )
    subparser.add_argument(
        "--no-verification",
        action="store_true",
        default=False,
        help="Disable verification via commit/gpg",
    )
    subparser.add_argument(
        "--dependencies",
        action="store_true",
        help="Also pull and update dependencies",
    )
    subparser.add_argument(
        "--clone-mode",
        choices=["ssh", "https", "shallow"],
        default="ssh",
        help=(
            "Specify the clone mode: ssh, https, or shallow "
            "(HTTPS shallow clone; default: ssh)"
        ),
    )
