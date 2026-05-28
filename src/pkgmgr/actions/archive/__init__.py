"""Archive fully-checked Markdown files into a README index, then delete them.

The archive action walks a directory for numbered ``NNN-topic.md`` files
(default pattern ``^\\d{3}-[^/]+\\.md$``), promotes every file with zero
unchecked ``- [ ]`` task-list markers into a ``## Archive`` index inside
the directory README, and deletes the per-file source. Useful for
keeping ``docs/requirements/`` (or any other task-tracked spec folder)
short and focused on open work.

The module was extracted from
``cli/contributing/requirements/archive`` in infinito-nexus-core so
every kpmx-managed repository can rely on the same archival convention
without copy-pasting the helpers.
"""

from __future__ import annotations

from .discovery import iter_archivable_files
from .inspect import count_unchecked_items, extract_h1
from .readme import existing_archive_entries, merge_archive_section
from .workflow import ArchivePlan, run_archive

__all__ = [
    "ArchivePlan",
    "count_unchecked_items",
    "existing_archive_entries",
    "extract_h1",
    "iter_archivable_files",
    "merge_archive_section",
    "run_archive",
]
