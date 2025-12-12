from __future__ import annotations

import sys


def should_delete_branch(force: bool) -> bool:
    """
    Ask whether the current branch should be deleted after a successful release.

    - If force=True: skip prompt and return True.
    - If non-interactive stdin: do NOT delete by default.
    """
    if force:
        return True
    if not sys.stdin.isatty():
        return False
    answer = input("Delete the current branch after release? [y/N] ").strip().lower()
    return answer in ("y", "yes")


def confirm_proceed_release() -> bool:
    """
    Ask whether to proceed with the REAL release after the preview phase.
    """
    try:
        answer = input("Proceed with the actual release? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return answer in ("y", "yes")
