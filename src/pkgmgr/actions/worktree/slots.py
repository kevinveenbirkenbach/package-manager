from __future__ import annotations

import os

SLOT_FILE = "pkgmgr-slot"


def used_slots(common_dir: str) -> set[int]:
    base = os.path.join(common_dir, "worktrees")
    slots: set[int] = set()
    for entry in os.listdir(base) if os.path.isdir(base) else []:
        try:
            with open(os.path.join(base, entry, SLOT_FILE), encoding="utf-8") as fh:
                slots.add(int(fh.read().strip()))
        except (OSError, ValueError):
            continue
    return slots


def next_slot(used: set[int]) -> int:
    slot = 1
    while slot in used:
        slot += 1
    return slot


def write_slot(path: str, slot: int) -> None:
    """
    Record a slot in the metadata of a worktree this process just added.

    Args:
        path: the new worktree, whose `.git` file names its metadata.
        slot: the slot to record.
    """
    with open(os.path.join(path, ".git"), encoding="utf-8") as fh:
        meta = os.path.normpath(
            os.path.join(path, fh.read().strip().removeprefix("gitdir: "))
        )
    with open(os.path.join(meta, SLOT_FILE), "w", encoding="utf-8") as fh:
        fh.write(f"{slot}\n")
