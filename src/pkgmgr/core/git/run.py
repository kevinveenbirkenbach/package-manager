from __future__ import annotations

import os
import subprocess

from .errors import GitNotRepositoryError, GitRunError

SCAN_FLAGS = (
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.hooksPath=/dev/null",
    "-c",
    "core.pager=cat",
    "-c",
    "gc.auto=0",
    "-c",
    "maintenance.auto=false",
    "-c",
    "log.showSignature=false",
)
SCAN_ENV = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_NO_LAZY_FETCH": "1",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_TERMINAL_PROMPT": "0",
    "GIT_ASKPASS": "/bin/false",
    "LC_ALL": "C",
}
SCAN_UNSET = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_EXTERNAL_DIFF",
    "GIT_PAGER",
    "PAGER",
)
SCAN_TIMEOUT = 60
# ref and remote names come from repositories an agent may write: one named
# like --output=<path> would otherwise make rev-list create that file
END_OF_OPTIONS = "--end-of-options"


def _is_not_repo_error(stderr: str) -> bool:
    msg = (stderr or "").lower()
    return "not a git repository" in msg


def _scan_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key not in SCAN_UNSET}
    return {**env, **SCAN_ENV}


def run(
    args: list[str],
    *,
    cwd: str = ".",
    preview: bool = False,
    scan: bool = False,
) -> str:
    """
    Run a Git command and return its stdout as a stripped string.

    Args:
        args: the git arguments.
        cwd: directory to run in.
        preview: print the command instead of running it.
        scan: read a repository an agent may have written: no fsmonitor, hook,
            pager, lazy fetch, replace object, system config or prompt, stdin
            closed, a timeout.

    Raises GitRunError (or a subclass) if execution fails or times out.
    """
    cmd = ["git", *SCAN_FLAGS, *args] if scan else ["git"] + args
    cmd_str = " ".join(cmd)

    if preview:
        print(f"[PREVIEW] Would run in {cwd!r}: {cmd_str}")
        return ""

    hardened = (
        {"env": _scan_env(), "stdin": subprocess.DEVNULL, "timeout": SCAN_TIMEOUT}
        if scan
        else {}
    )
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            **hardened,
        )
    except subprocess.TimeoutExpired as exc:
        err = GitRunError(f"Git command timed out in {cwd!r}: {cmd_str}")
        err.cwd, err.cmd, err.cmd_str, err.returncode = cwd, cmd, cmd_str, -1
        err.stdout, err.stderr = "", ""
        raise err from exc
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
