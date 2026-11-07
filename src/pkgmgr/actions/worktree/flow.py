from __future__ import annotations

import os
import secrets
import stat
from contextlib import suppress
from dataclasses import dataclass, field

import yaml

from pkgmgr.actions.branch.nofollow import DIR_FLAGS
from pkgmgr.core.git.errors import GitBaseError
from pkgmgr.core.git.run import run

FLOW_DIR = "pkgmgr"
FLOW_FILE = "flow.yml"
RELATIVE = f"{FLOW_DIR}/{FLOW_FILE}"
VERSION = 1
MAX_BYTES = 64 * 1024
FOLDER_MODE = 0o700
FILE_MODE = 0o600
KEYS = ("version", "branch", "pull", "push")
REQUIRED = ("version", "pull", "push")
# O_NONBLOCK: opening a planted FIFO for reading would block until a writer comes
READ_FLAGS = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
WRITE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
DETACHED = "a detached HEAD"
NONE_LISTED = "(none)"


class FlowError(ValueError):
    pass


@dataclass
class Flow:
    pull: list[str] = field(default_factory=list)
    push: list[str] = field(default_factory=list)
    branch: str | None = None
    source: str = "none"
    warnings: list[str] = field(default_factory=list)


def describe(exc: BaseException) -> str:
    return (str(exc).strip().splitlines() or [type(exc).__name__])[0]


def _ref_format(name: str) -> bool:
    # check-ref-format needs no repository, so / keeps any repository config
    # out; --branch would expand @{-N} into another name inside one
    try:
        return (
            run(["check-ref-format", "--branch", name], cwd=os.sep, scan=True) == name
        )
    except (GitBaseError, OSError, ValueError):
        return False


def check_name(kind: str, name: object) -> str:
    """
    Args:
        kind: pull, push or branch, for the message.
        name: an entry from the file or the command line.

    Returns:
        name, once it is a string git accepts as a branch name that does not
        start with `-`; a remote-tracking name such as origin/main passes.

    Raises:
        FlowError: name is anything else.
    """
    if not isinstance(name, str) or name.startswith("-") or not _ref_format(name):
        raise FlowError(f"{kind} {name!r} is not a valid branch name")
    return name


def check_names(kind: str, names: object) -> list[str]:
    """
    Args:
        kind: pull or push, for the message.
        names: the list from the file or the command line.

    Returns:
        The names in order, each passed through check_name.

    Raises:
        FlowError: names is not a list or an entry is invalid.
    """
    if not isinstance(names, list):
        raise FlowError(f"{kind} must be a list of branch names")
    return [check_name(kind, name) for name in names]


def _folder(git_dir: str, create: bool) -> int:
    parent = os.open(git_dir, os.O_RDONLY | os.O_DIRECTORY)
    try:
        if create:
            with suppress(FileExistsError):
                os.mkdir(FLOW_DIR, FOLDER_MODE, dir_fd=parent)
        return os.open(FLOW_DIR, DIR_FLAGS, dir_fd=parent)
    finally:
        os.close(parent)


def _read_text(git_dir: str) -> str | None:
    try:
        folder = _folder(git_dir, create=False)
    except FileNotFoundError:
        return None
    try:
        fd = os.open(FLOW_FILE, READ_FLAGS, dir_fd=folder)
    except FileNotFoundError:
        return None
    finally:
        os.close(folder)
    # os.fdopen refuses a directory but leaves its fd open, so check first
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        os.close(fd)
        raise FlowError("not a regular file")
    with os.fdopen(fd, "rb") as fh:
        data = fh.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise FlowError(f"larger than {MAX_BYTES} bytes")
    return data.decode("utf-8")


def _parse(text: str) -> tuple[str | None, list[str], list[str]]:
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise FlowError("not a mapping")
    unknown = [repr(key) for key in data if key not in KEYS]
    if unknown:
        raise FlowError(f"unknown keys {', '.join(unknown)}")
    missing = [key for key in REQUIRED if key not in data]
    if missing:
        raise FlowError(f"missing keys {', '.join(missing)}")
    # bool is an int, and True == 1
    if type(data["version"]) is not int or data["version"] != VERSION:
        raise FlowError(f"version must be {VERSION}")
    branch = data.get("branch")
    if branch is not None:
        check_name("branch", branch)
    return branch, check_names("pull", data["pull"]), check_names("push", data["push"])


def read_flow(git_dir: str) -> Flow:
    """
    Read `<git_dir>/pkgmgr/flow.yml`, which an agent may have written.

    Args:
        git_dir: the worktree's own git directory.

    Returns:
        The flow with source file; source none when there is no file; source
        invalid, empty lists and a warning when the file is a symbolic link,
        no regular file, larger than MAX_BYTES or malformed. Never raises.
    """
    try:
        text = _read_text(git_dir)
        if text is None:
            return Flow()
        branch, pull, push = _parse(text)
    # RecursionError: safe_load recurses once per nesting level
    except (OSError, ValueError, yaml.YAMLError, RecursionError) as exc:
        return Flow(source="invalid", warnings=[f"{RELATIVE} ignored: {describe(exc)}"])
    return Flow(pull=pull, push=push, branch=branch, source="file")


def write_flow(
    git_dir: str, branch: str | None, pull: list[str], push: list[str]
) -> None:
    """
    Replace the flow atomically, never writing through a symbolic link.

    Args:
        git_dir: the worktree's own git directory.
        branch: the worktree's branch now; None when detached.
        pull: refs merged into the branch, in order, already through check_names.
        push: branches the branch is merged into, in order, likewise checked.

    Raises:
        OSError: `pkgmgr` is a symbolic link or no directory, or a write failed.
    """
    data = {"version": VERSION, "branch": branch, "pull": pull, "push": push}
    text = yaml.safe_dump(data, sort_keys=False, default_flow_style=False)
    folder = _folder(git_dir, create=True)
    tmp = f".{FLOW_FILE}.{secrets.token_hex(8)}"
    try:
        fd = os.open(tmp, WRITE_FLAGS, FILE_MODE, dir_fd=folder)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, FLOW_FILE, src_dir_fd=folder, dst_dir_fd=folder)
    finally:
        with suppress(FileNotFoundError):
            os.unlink(tmp, dir_fd=folder)
        os.close(folder)


def clear_flow(git_dir: str) -> None:
    """
    Remove the flow file; a symbolic link in its place goes, never its target.

    Args:
        git_dir: the worktree's own git directory.

    Raises:
        OSError: `pkgmgr` is a symbolic link or no directory, or the unlink failed.
    """
    try:
        folder = _folder(git_dir, create=False)
    except FileNotFoundError:
        return
    try:
        with suppress(FileNotFoundError):
            os.unlink(FLOW_FILE, dir_fd=folder)
    finally:
        os.close(folder)


def mismatch(flow: Flow, branch: str | None) -> list[str]:
    """
    Args:
        flow: a flow from read_flow.
        branch: the worktree's current branch; None when detached.

    Returns:
        One warning when the file was written on another branch, else none.
    """
    if flow.source != "file" or flow.branch == branch:
        return []
    warning = (
        f"flow was set on {flow.branch or DETACHED}, "
        f"the worktree is on {branch or DETACHED}"
    )
    return [warning]
