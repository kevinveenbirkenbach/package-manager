"""Orchestrator for archiving fully-checked Markdown files."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from pathlib import Path

from .discovery import iter_archivable_files
from .inspect import count_unchecked_items, extract_h1
from .readme import existing_archive_entries, merge_archive_section


@dataclass(frozen=True)
class ArchivePlan:
    """Outcome of an archive analysis run.

    Attributes:
        archived: ``(source_path, title)`` for every file that was (or
            would be) archived. Order matches the original directory
            listing.
        skipped_incomplete: ``(source_path, unchecked_count)`` for files
            that still hold ``- [ ]`` markers.
        skipped_without_h1: files that had no H1 heading to use as title.
        new_entries: titles that will be appended to the README index.
        existing_entries: titles already present in the README index.
    """

    archived: list[tuple[Path, str]]
    skipped_incomplete: list[tuple[Path, int]]
    skipped_without_h1: list[Path]
    new_entries: list[str]
    existing_entries: set[str]


def _bucket_files(
    files: list[Path],
) -> tuple[
    list[tuple[Path, str]],
    list[tuple[Path, int]],
    list[Path],
]:
    plan: list[tuple[Path, str]] = []
    skipped_incomplete: list[tuple[Path, int]] = []
    skipped_without_h1: list[Path] = []
    for path in files:
        unchecked = count_unchecked_items(path)
        if unchecked > 0:
            skipped_incomplete.append((path, unchecked))
            continue
        title = extract_h1(path)
        if title is None:
            skipped_without_h1.append(path)
            continue
        plan.append((path, title))
    return plan, skipped_incomplete, skipped_without_h1


def _dedupe_titles(
    plan: list[tuple[Path, str]], already_archived: set[str]
) -> list[str]:
    new_entries: list[str] = []
    for _path, title in plan:
        if title in already_archived or title in new_entries:
            continue
        new_entries.append(title)
    return new_entries


def run_archive(
    directory: Path,
    readme_path: Path,
    *,
    dry_run: bool = False,
    include_template: bool = False,
) -> ArchivePlan:
    """Walk *directory* and archive every fully-checked file into *readme_path*.

    Returns an :class:`ArchivePlan` describing the outcome. When
    ``dry_run`` is true no files are deleted and the README is not
    rewritten — the plan still reflects what *would* happen.

    Raises ``FileNotFoundError`` if *directory* or *readme_path* does
    not exist.
    """
    if not directory.is_dir():
        raise FileNotFoundError(f"Archive directory not found: {directory}")
    if not readme_path.is_file():
        raise FileNotFoundError(f"README not found: {readme_path}")

    files = iter_archivable_files(directory, include_template=include_template)
    readme_text = readme_path.read_text(encoding="utf-8")
    already_archived = existing_archive_entries(readme_text)

    archived, skipped_incomplete, skipped_without_h1 = _bucket_files(files)
    new_entries = _dedupe_titles(archived, already_archived)

    if not dry_run and new_entries:
        merged_text = merge_archive_section(readme_text, new_entries)
        if merged_text != readme_text:
            readme_path.write_text(merged_text, encoding="utf-8")

    if not dry_run:
        for path, _title in archived:
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    return ArchivePlan(
        archived=archived,
        skipped_incomplete=skipped_incomplete,
        skipped_without_h1=skipped_without_h1,
        new_entries=new_entries,
        existing_entries=already_archived,
    )
