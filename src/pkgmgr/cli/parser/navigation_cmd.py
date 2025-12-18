#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse

from .common import add_identifier_arguments


def add_navigation_subparsers(
    subparsers: argparse._SubParsersAction,
) -> None:
    """
    Register path / explore / terminal / code / shell commands.
    """
    path_parser = subparsers.add_parser(
        "path",
        help="Print the path(s) of repository/repositories",
    )
    add_identifier_arguments(path_parser)

    explore_parser = subparsers.add_parser(
        "explore",
        help="Open repository in Nautilus file manager",
    )
    add_identifier_arguments(explore_parser)

    terminal_parser = subparsers.add_parser(
        "terminal",
        help="Open repository in a new GNOME Terminal tab",
    )
    add_identifier_arguments(terminal_parser)

    code_parser = subparsers.add_parser(
        "code",
        help="Open repository workspace with VS Code",
    )
    add_identifier_arguments(code_parser)

    shell_parser = subparsers.add_parser(
        "shell",
        help="Execute a shell command in each repository",
    )
    add_identifier_arguments(shell_parser)
    shell_parser.add_argument(
        "-c",
        "--command",
        nargs=argparse.REMAINDER,
        dest="shell_command",
        help=("The shell command (and its arguments) to execute in each repository"),
        default=[],
    )
