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
        stdout = exc.stdout or ""

        if _is_not_repo_error(stderr):
            err = GitNotRepositoryError(
                f"Not a git repository: {cwd!r}\nCommand: {cmd_str}\nSTDERR:\n{stderr}"
            )
            # Attach details for callers who want to debug
            err.cwd = cwd
            err.cmd = cmd
            err.cmd_str = cmd_str
            err.returncode = exc.returncode
            err.stdout = stdout
            err.stderr = stderr
            raise err from exc

        err = GitRunError(
            f"Git command failed in {cwd!r}: {cmd_str}\n"
            f"Exit code: {exc.returncode}\n"
            f"STDOUT:\n{stdout}\n"
            f"STDERR:\n{stderr}"
        )
        # Attach details for callers who want to debug
        err.cwd = cwd
        err.cmd = cmd
        err.cmd_str = cmd_str
        err.returncode = exc.returncode
        err.stdout = stdout
        err.stderr = stderr
        raise err from exc

    return result.stdout.strip()
