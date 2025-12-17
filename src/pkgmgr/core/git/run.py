from __future__ import annotations

import subprocess
from typing import List

from .errors import GitRunError, GitNotRepositoryError


def _is_not_repo_error(stderr: str) -> bool:
    msg = (stderr or "").lower()
    return "not a git repository" in msg


def run(
    args: List[str],
    *,
    cwd: str = ".",
    preview: bool = False,
) -> str:
    """
    Run a Git command and return its stdout as a stripped string.

    If preview=True, the command is printed but NOT executed.

    Raises GitRunError (or a subclass) if execution fails.
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
        stderr = exc.stderr or ""
        if _is_not_repo_error(stderr):
            raise GitNotRepositoryError(
                f"Not a git repository: {cwd!r}\n"
                f"Command: {cmd_str}\n"
                f"STDERR:\n{stderr}"
            ) from exc

        raise GitRunError(
            f"Git command failed in {cwd!r}: {cmd_str}\n"
            f"Exit code: {exc.returncode}\n"
            f"STDOUT:\n{exc.stdout}\n"
            f"STDERR:\n{stderr}"
        ) from exc

    return result.stdout.strip()
