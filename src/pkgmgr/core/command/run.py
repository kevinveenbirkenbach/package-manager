import subprocess
import sys
from typing import List, Optional, Union


CommandType = Union[str, List[str]]


def run_command(
    cmd: CommandType,
    cwd: Optional[str] = None,
    preview: bool = False,
    allow_failure: bool = False,
) -> subprocess.CompletedProcess:
    """
    Run a command and optionally exit on error.

    - If `cmd` is a string, it is executed with `shell=True`.
    - If `cmd` is a list of strings, it is executed without a shell.
    """
    if isinstance(cmd, str):
        display = cmd
    else:
        display = " ".join(cmd)

    where = cwd or "."

    if preview:
        print(f"[Preview] In '{where}': {display}")
        # Fake a successful result; most callers ignore the return value anyway
        return subprocess.CompletedProcess(cmd, 0)  # type: ignore[arg-type]

    print(f"Running in '{where}': {display}")

    if isinstance(cmd, str):
        result = subprocess.run(cmd, cwd=cwd, shell=True)
    else:
        result = subprocess.run(cmd, cwd=cwd)

    if result.returncode != 0 and not allow_failure:
        print(f"Command failed with exit code {result.returncode}. Exiting.")
        sys.exit(result.returncode)

    return result
