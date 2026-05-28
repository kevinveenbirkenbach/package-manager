from __future__ import annotations

import argparse


def add_archive_subparser(subparsers: argparse._SubParsersAction) -> None:
    """Register the archive subcommand.

    Walks a directory of numbered ``NNN-topic.md`` files, promotes every
    file whose ``- [ ]`` checklist is fully checked into the directorys
    README ``## Archive`` section, then deletes the source file.
    """
    parser = subparsers.add_parser(
        "archive",
        help=(
            "Archive fully-checked Markdown spec files (NNN-topic.md) "
            "into the directorys README and delete them."
        ),
        description=(
            "Walk DIR for files that match the numbered "
            "NNN-topic.md naming, promote every file with zero "
            "unchecked `- [ ]` items into READMEs ## Archive section, "
            "then delete the source file. Files with unchecked items are "
            "skipped. Use --dry-run to preview without writing."
        ),
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default="docs/requirements",
        help=(
            "Directory to scan for archivable Markdown files. "
            "Defaults to docs/requirements (relative to the current "
            "working directory)."
        ),
    )
    parser.add_argument(
        "--readme",
        default=None,
        help=(
            "Path to the README that holds the ## Archive index. "
            "Defaults to <directory>/README.md."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned changes without modifying or deleting anything.",
    )
    parser.add_argument(
        "--include-template",
        action="store_true",
        help=(
            "Also archive and delete 000-template.md. Off by default "
            "because contributor guides typically reference it."
        ),
    )
