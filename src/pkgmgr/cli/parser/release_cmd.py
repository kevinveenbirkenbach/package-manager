#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse

from .common import add_identifier_arguments


def add_release_subparser(
    subparsers: argparse._SubParsersAction,
) -> None:
    """
    Register the release command.
    """
    release_parser = subparsers.add_parser(
        "release",
        help=(
            "Create a release for repository/ies by incrementing version "
            "and updating the changelog."
        ),
    )

    release_parser.add_argument(
        "release_type",
        choices=["major", "minor", "patch"],
        help="Type of version increment for the release (major, minor, patch).",
    )

    release_parser.add_argument(
        "-m",
        "--message",
        default=None,
        help="Optional release message to add to the changelog and tag.",
    )

    add_identifier_arguments(release_parser)

    release_parser.add_argument(
        "--close",
        action="store_true",
        help=(
            "Close the current branch after a successful release in each "
            "repository, if it is not main/master."
        ),
    )

    release_parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help=(
            "Skip the interactive preview+confirmation step and run the "
            "release directly."
        ),
    )

    release_parser.add_argument(
        "--no-publish",
        action="store_true",
        help="Do not run publish automatically after a successful release.",
    )
