from __future__ import annotations

import selectors
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
    Run a command with live output while capturing stdout/stderr.

    - Output is streamed live to the terminal.
    - Output is captured in memory.
    - On failure, captured stdout/stderr are printed again so errors are never lost.
    - Command is executed exactly once.
    """
    display = cmd if isinstance(cmd, str) else " ".join(cmd)
    where = cwd or "."

    if preview:
        print(f"[Preview] In '{where}': {display}")
        return subprocess.CompletedProcess(cmd, 0)  # type: ignore[arg-type]

    print(f"Running in '{where}': {display}")

    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        shell=isinstance(cmd, str),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    assert process.stdout is not None
    assert process.stderr is not None

    sel = selectors.DefaultSelector()
    sel.register(process.stdout, selectors.EVENT_READ, data="stdout")
    sel.register(process.stderr, selectors.EVENT_READ, data="stderr")

    stdout_lines: List[str] = []
    stderr_lines: List[str] = []

    try:
        while sel.get_map():
            for key, _ in sel.select():
                stream = key.fileobj
                which = key.data

                line = stream.readline()
                if line == "":
                    # EOF: stop watching this stream
                    try:
                        sel.unregister(stream)
                    except Exception:
                        pass
                    continue

                if which == "stdout":
                    stdout_lines.append(line)
                    print(line, end="")
                else:
                    stderr_lines.append(line)
                    print(line, end="", file=sys.stderr)
    finally:
        # Ensure we don't leak FDs
        try:
            sel.close()
        finally:
            try:
                process.stdout.close()
            except Exception:
                pass
            try:
                process.stderr.close()
            except Exception:
                pass

    returncode = process.wait()

    if returncode != 0 and not allow_failure:
        print("\n[pkgmgr] Command failed, captured diagnostics:", file=sys.stderr)
        print(f"[pkgmgr] Failed command: {display}", file=sys.stderr)

        if stdout_lines:
            print("----- stdout -----")
            print("".join(stdout_lines), end="")

        if stderr_lines:
            print("----- stderr -----", file=sys.stderr)
            print("".join(stderr_lines), end="", file=sys.stderr)

        print(f"Command failed with exit code {returncode}. Exiting.")
        sys.exit(returncode)

    return subprocess.CompletedProcess(
        cmd,
        returncode,
        stdout="".join(stdout_lines),
        stderr="".join(stderr_lines),
    )
