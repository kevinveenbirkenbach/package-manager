"""Locate archivable Markdown files under a target directory."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

DEFAULT_FILENAME_PATTERN = re.compile(r"^\d{3}-[^/]+\.md$")
TEMPLATE_FILENAME = "000-template.md"


def iter_archivable_files(
    directory: Path,
    *,
    include_template: bool = False,
    pattern: re.Pattern[str] = DEFAULT_FILENAME_PATTERN,
    template_filename: str = TEMPLATE_FILENAME,
) -> list[Path]:
    """Return all files in *directory* whose name matches *pattern*, sorted.

    ``000-template.md`` (or whatever *template_filename* matches) is
    excluded unless *include_template* is true. The check is filename
    based; nested directories are not traversed.
    """
    if not directory.is_dir():
        return []
    files: list[Path] = []
    for path in sorted(directory.iterdir()):
        if not path.is_file() or not pattern.match(path.name):
            continue
        if not include_template and path.name == template_filename:
            continue
        files.append(path)
    return files


def filter_archivable_files(
    paths: Iterable[Path],
    *,
    include_template: bool = False,
    pattern: re.Pattern[str] = DEFAULT_FILENAME_PATTERN,
    template_filename: str = TEMPLATE_FILENAME,
) -> list[Path]:
    """Same predicate as :func:`iter_archivable_files`, applied to an iterable."""
    result: list[Path] = []
    for path in paths:
        if not path.is_file() or not pattern.match(path.name):
            continue
        if not include_template and path.name == template_filename:
            continue
        result.append(path)
    return result
