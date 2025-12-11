#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse

from .common import add_identifier_arguments


def add_changelog_subparser(
    subparsers: argparse._SubParsersAction,
) -> None:
    """
    Register the changelog command.
    """
    changelog_parser = subparsers.add_parser(
        "changelog",
        help=(
            "Show changelog derived from Git history. "
            "By default, shows the changes between the last two SemVer tags."
        ),
    )
    changelog_parser.add_argument(
        "range",
        nargs="?",
        default="",
        help=(
            "Optional tag or range (e.g. v1.2.3 or v1.2.0..v1.2.3). "
            "If omitted, the changelog between the last two SemVer "
            "tags is shown."
        ),
    )
    add_identifier_arguments(changelog_parser)
