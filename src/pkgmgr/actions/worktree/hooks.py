from __future__ import annotations

import os
import re
import shutil
import signal
import subprocess
import time

from .trust import root_resolved, trusted_path

INIT_HOOK = "worktree-init"
FINI_HOOK = "worktree-fini"
MAKEFILES = ("GNUmakefile", "makefile", "Makefile")
MAKEFILE_LIMIT = 1 << 20
HOOK_TIMEOUT = 1800
HOOK_GRACE = 5
PLACEHOLDER = re.compile(r"\{(path|slot)\}")


def defined_in(path: str, target: str) -> str | None:
    """
    Name the makefile in path that defines target, read as text and never run:
    make expands $(shell) and include lines even under -n.

    Args:
        path: directory that may hold a makefile.
        target: make target name.

    Returns:
        The first makefile, in make's lookup order, with a `<target>:` rule;
        None when none has one.
    """
    rule = re.compile(rf"^{re.escape(target)}\s*:", re.MULTILINE)
    for name in MAKEFILES:
        file = os.path.join(path, name)
        if os.path.islink(file) or not os.path.isfile(file):
            continue
        with open(file, encoding="utf-8", errors="replace") as fh:
            if rule.search(fh.read(MAKEFILE_LIMIT)):
                return name
    return None


def hook_command(name: str, argv: list[str], path: str, slot: int | None) -> list[str]:
    """
    Fill a pinned hook command in one pass and resolve its program.

    Args:
        name: the hook, for error messages.
        argv: the command pinned in the `worktree_hooks` config.
        path: the worktree, replacing `{path}`.
        slot: the worktree's slot, replacing `{slot}`; None leaves it as is.

    Returns:
        The argv to run; its program is an absolute path, for a bare name the
        resolved file that was checked, so a multi-call binary sees that
        file's name; pin the link's absolute path to keep the link's name.

    Raises:
        RuntimeError: the program is neither absolute nor a bare name found,
            as a root-controlled file, on a root-owned PATH entry no group or
            other user can write; anything relative resolves in the worktree.
    """

    def fill(match: re.Match[str]) -> str:
        if match.group(1) == "path":
            return path
        return match.group(0) if slot is None else str(slot)

    filled = [PLACEHOLDER.sub(fill, arg) for arg in argv]
    program = filled[0] if filled else ""
    if not os.path.isabs(program):
        found = (
            shutil.which(program, path=trusted_path())
            if program and "/" not in program
            else None
        )
        resolved = root_resolved(found) if found else None
        if resolved is None:
            raise RuntimeError(
                f"{name} pin {program!r} is neither an absolute path nor a "
                "root-owned command on a root-owned PATH entry"
            )
        program = resolved
    return [program, *filled[1:]]


def run_hook(
    name: str, command: list[str], path: str, *, check: bool, **kwargs
) -> subprocess.CompletedProcess:
    """
    Run a resolved hook command in the worktree.

    Args:
        name: the hook, for error messages.
        command: the argv from hook_command.
        path: the worktree to run in.
        check: raise CalledProcessError on a non-zero exit.
        kwargs: further subprocess.Popen arguments, such as output handling.

    Returns:
        The completed process; stdin was closed, PATH held only its
        root-controlled entries and HOOK_TIMEOUT applied to its whole process
        group.

    Raises:
        RuntimeError: the hook ran longer than HOOK_TIMEOUT, or no PATH entry
            is root-controlled.
    """
    with subprocess.Popen(
        command,
        cwd=path,
        stdin=subprocess.DEVNULL,
        env={**os.environ, "PATH": trusted_path()},
        start_new_session=True,
        **kwargs,
    ) as process:
        try:
            stdout, stderr = process.communicate(timeout=HOOK_TIMEOUT)
        except subprocess.TimeoutExpired as exc:
            _stop_group(process)
            raise RuntimeError(f"{name} timed out after {HOOK_TIMEOUT} s") from exc
    if check and process.returncode:
        raise subprocess.CalledProcessError(
            process.returncode, command, output=stdout, stderr=stderr
        )
    return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)


def _stop_group(process: subprocess.Popen) -> None:
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, sig)
        except OSError:
            return
        deadline = time.monotonic() + HOOK_GRACE
        while time.monotonic() < deadline:
            process.poll()
            try:
                os.killpg(process.pid, 0)
            except OSError:
                return
            time.sleep(0.05)
