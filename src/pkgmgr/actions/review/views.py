from __future__ import annotations

import os
from urllib.parse import quote

from .model import FileDiff, FileView, Hunk

BINARY_DETAIL = "Binary file, contents not shown."


def _first_changed_line(hunks: tuple[Hunk, ...]) -> int:
    for hunk in hunks:
        position = hunk.new_start
        for line in hunk.lines:
            if line.kind in ("add", "del"):
                return max(position, 1)
            if line.new is not None:
                position = line.new + 1
    return 1


def _truncate(hunks: tuple[Hunk, ...], limit: int) -> tuple[tuple[Hunk, ...], int]:
    shown: list[Hunk] = []
    budget = limit
    for hunk in hunks:
        if budget <= 0:
            break
        lines = hunk.lines[:budget]
        shown.append(Hunk(hunk.header, hunk.new_start, lines))
        budget -= len(lines)
    total = sum(len(hunk.lines) for hunk in hunks)
    return tuple(shown), total - (limit - budget)


def file_view(
    diff: FileDiff, anchor: str, top: str, limit: int, detail: str | None
) -> FileView:
    link_base = None
    if diff.new_path is not None:
        link_base = "vscode://file" + quote(os.path.join(top, diff.new_path))
    hunks, hidden = _truncate(diff.hunks, limit)
    return FileView(
        anchor=anchor,
        diff=diff,
        detail=detail,
        link_base=link_base,
        link=None
        if link_base is None
        else f"{link_base}:{_first_changed_line(diff.hunks)}",
        hunks=hunks,
        hidden=hidden,
    )


def file_views(
    diffs: list[FileDiff], prefix: str, top: str, limit: int
) -> tuple[FileView, ...]:
    return tuple(
        file_view(
            diff,
            f"{prefix}-{index}",
            top,
            limit,
            BINARY_DETAIL if diff.binary else None,
        )
        for index, diff in enumerate(diffs, 1)
    )
