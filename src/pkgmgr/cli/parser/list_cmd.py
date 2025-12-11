#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse

from .common import add_identifier_arguments


def add_list_subparser(
    subparsers: argparse._SubParsersAction,
) -> None:
    """
    Register the list command.
    """
    list_parser = subparsers.add_parser(
        "list",
        help="List all repositories with details and status",
    )
    add_identifier_arguments(list_parser)
    list_parser.add_argument(
        "--status",
        type=str,
        default="",
        help=(
            "Filter repositories by status (case insensitive). "
            "Use /regex/ for regular expressions."
        ),
    )
    list_parser.add_argument(
        "--description",
        action="store_true",
        help=(
            "Show an additional detailed section per repository "
            "(description, homepage, tags, categories, paths)."
        ),
    )
