from __future__ import annotations

import argparse

from .common import add_identifier_arguments


def add_publish_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "publish",
        help="Publish repository artifacts (e.g. PyPI) based on MIRRORS.",
    )
    add_identifier_arguments(parser)

    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Disable interactive credential prompts (CI mode).",
    )
