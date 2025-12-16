from __future__ import annotations

import subprocess
from typing import List

from .errors import GitError


def run(
    args: List[str],
    *,
    cwd: str = ".",
    preview: bool = False,
) -> str:
    """
    Run a Git command and return its stdout as a stripped string.

    If preview=True, the command is printed but NOT executed.

    Raises GitError if execution fails.
    """
    cmd = ["git"] + args
    cmd_str = " ".join(cmd)

    if preview:
        print(f"[PREVIEW] Would run in {cwd!r}: {cmd_str}")
        return ""

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise GitError(
            f"Git command failed in {cwd!r}: {cmd_str}\n"
            f"Exit code: {exc.returncode}\n"
            f"STDOUT:\n{exc.stdout}\n"
            f"STDERR:\n{exc.stderr}"
        ) from exc

    return result.stdout.strip()
