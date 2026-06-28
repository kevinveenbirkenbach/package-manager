from __future__ import annotations

import argparse


def add_code_scanning_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the code-scanning subcommand.

    Downloads a repository's GitHub code scanning alerts (and analysis
    metadata) into a timestamped directory for offline analysis, using the
    ``gh`` CLI for authentication.
    """
    parser = subparsers.add_parser(
        "code-scanning",
        help="Download GitHub code scanning results for offline analysis.",
        description=(
            "Fetch all code scanning alerts (plus analysis metadata) for a "
            "repository via the gh CLI and write them, with a readable "
            "summary, into a timestamped directory. Defaults to the current "
            "repository and /tmp/<repo>/code-scanner/<YYYYMMDDHHMMSS>."
        ),
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="Target repository as OWNER/REPO (default: current repo via gh).",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help=("Output directory (default: /tmp/<repo>/code-scanner/<YYYYMMDDHHMMSS>)."),
    )
    parser.add_argument(
        "--state",
        default=None,
        choices=["open", "closed", "dismissed", "fixed"],
        help="Only download alerts in this state (default: all states).",
    )
