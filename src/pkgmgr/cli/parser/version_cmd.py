#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse

from .common import add_identifier_arguments


def add_version_subparser(
    subparsers: argparse._SubParsersAction,
) -> None:
    """
    Register the version command.
    """
    version_parser = subparsers.add_parser(
        "version",
        help=(
            "Show version information for repository/ies "
            "(git tags, pyproject.toml, flake.nix, PKGBUILD, debian, spec, "
            "Ansible Galaxy)."
        ),
    )
    add_identifier_arguments(version_parser)
