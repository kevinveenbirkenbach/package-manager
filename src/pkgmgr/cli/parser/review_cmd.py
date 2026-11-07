from __future__ import annotations

import argparse


def _positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError(f"must be a positive integer, got {value}")
    return number


def add_review_subparser(subparsers: argparse._SubParsersAction) -> None:
    parser = subparsers.add_parser(
        "review",
        help="Render the working copy's changes as a local HTML review page.",
        description=(
            "Write a self-contained HTML page showing the staged, unstaged and "
            "untracked changes of the current git working copy (plus the commits "
            "of REF..HEAD with --base) and print its file:// URL."
        ),
    )
    parser.add_argument(
        "--out",
        required=True,
        metavar="FILE",
        help="Write the HTML page to FILE; parent directories are created.",
    )
    parser.add_argument(
        "--max-file-lines",
        required=True,
        type=_positive_int,
        metavar="N",
        help="Show at most N diff lines per file and summarise the rest.",
    )
    parser.add_argument(
        "--base",
        metavar="REF",
        help="Add a Commits section for REF..HEAD; omitted means no Commits section.",
    )
    parser.add_argument(
        "--note",
        action="append",
        default=[],
        metavar="FILE",
        help="Show FILE verbatim in a panel at the top; repeatable.",
    )
