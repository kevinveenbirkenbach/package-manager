from __future__ import annotations

import errno
import os
import stat

from .model import FileDiff, FileView, Hunk, Line, Note, ReviewError
from .repo import git_text
from .views import BINARY_DETAIL, file_view

READ_MAX_BYTES = 1024 * 1024
BINARY_SNIFF_BYTES = 8000


def _listed(path: str, binary: bool) -> FileDiff:
    return FileDiff(
        old_path=None,
        new_path=path,
        status="untracked",
        binary=binary,
        mode_change=None,
        hunks=(),
    )


def _read_regular(path: str, limit: int) -> tuple[bytes, int] | None:
    """
    Args:
        path: Absolute path, opened one component at a time without following
            a symbolic link anywhere along it.
        limit: Most bytes to read.

    Returns:
        The bytes read and the file size, or None when a component is a
        symbolic link or the target is not a regular file.
    """
    names = [name for name in path.split(os.sep) if name not in ("", ".")]
    fd = os.open(os.sep, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for index, name in enumerate(names, 1):
            kind = os.O_NONBLOCK if index == len(names) else os.O_DIRECTORY
            child = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | kind, dir_fd=fd)
            os.close(fd)
            fd = child
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            return None
        with os.fdopen(os.dup(fd), "rb") as handle:
            return handle.read(limit), info.st_size
    except OSError as exc:
        if exc.errno in (errno.ELOOP, errno.ENOTDIR):
            return None
        raise
    finally:
        os.close(fd)


def _untracked_file(path: str, top: str) -> tuple[FileDiff, str | None]:
    try:
        read = _read_regular(os.path.join(top, path), READ_MAX_BYTES + 1)
    except OSError as exc:
        return _listed(path, False), f"Unreadable: {exc.strerror}."
    if read is None:
        return _listed(path, False), "Not a regular file, contents not shown."
    data, size = read
    if len(data) > READ_MAX_BYTES:
        return _listed(path, False), f"Large file ({size} bytes), contents not shown."
    if b"\0" in data[:BINARY_SNIFF_BYTES]:
        return _listed(path, True), BINARY_DETAIL
    lines = data.decode("utf-8", "replace").split("\n")
    if lines[-1] == "":
        lines.pop()
    added = tuple(
        Line("add", None, number, text) for number, text in enumerate(lines, 1)
    )
    hunks = (Hunk(f"@@ -0,0 +1,{len(added)} @@", 1, added),) if added else ()
    return (
        FileDiff(
            old_path=None,
            new_path=path,
            status="untracked",
            binary=False,
            mode_change=None,
            hunks=hunks,
        ),
        None,
    )


def untracked_views(top: str, limit: int) -> tuple[FileView, ...]:
    listing = git_text(["ls-files", "--others", "--exclude-standard", "-z"], top)
    views = []
    for index, path in enumerate(sorted(p for p in listing.split("\0") if p), 1):
        diff, detail = _untracked_file(path, top)
        views.append(file_view(diff, f"untracked-{index}", top, limit, detail))
    return tuple(views)


def read_note(path: str, cwd: str) -> Note:
    try:
        read = _read_regular(
            os.path.abspath(os.path.join(cwd, path)), READ_MAX_BYTES + 1
        )
    except OSError as exc:
        raise ReviewError(f"cannot read note {path!r}: {exc.strerror}") from None
    if read is None:
        raise ReviewError(
            f"cannot read note {path!r}: a symbolic link or not a regular file"
        )
    data, size = read
    if len(data) > READ_MAX_BYTES:
        raise ReviewError(
            f"cannot read note {path!r}: {size} bytes, more than {READ_MAX_BYTES}"
        )
    return Note(title=os.path.basename(path), text=data.decode("utf-8", "replace"))
