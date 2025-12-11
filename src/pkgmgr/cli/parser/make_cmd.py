#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse

from .common import add_identifier_arguments


def add_make_subparsers(
    subparsers: argparse._SubParsersAction,
) -> None:
    """
    Register make command and its subcommands.
    """
    make_parser = subparsers.add_parser(
        "make",
        help="Executes make commands",
    )
    add_identifier_arguments(make_parser)
    make_subparsers = make_parser.add_subparsers(
        dest="subcommand",
        help="Make subcommands",
        required=True,
    )

    make_install = make_subparsers.add_parser(
        "install",
        help="Executes the make install command",
    )
    add_identifier_arguments(make_install)

    make_deinstall = make_subparsers.add_parser(
        "deinstall",
        help="Executes the make deinstall command",
    )
    add_identifier_arguments(make_deinstall)
