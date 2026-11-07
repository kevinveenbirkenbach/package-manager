from __future__ import annotations

import os
import shutil

DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def canonical(path: str) -> bool:
    """
    Args:
        path: a path as git or a plan names it.

    Returns:
        True when path is absolute and already its own realpath: no symbolic
        link and no `..` component that the kernel could resolve elsewhere.
    """
    return os.path.isabs(path) and os.path.realpath(path) == path


def remove_tree(path: str) -> None:
    """
    Delete a directory tree without following a symbolic link anywhere on
    the way to it, even one swapped in after the caller checked the path.

    Args:
        path: absolute, canonical directory to delete.

    Raises:
        OSError: a component of path is a symbolic link or missing, or the
            deletion failed.
    """
    parent, name = os.path.split(path)
    fd = os.open(os.sep, os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in [c for c in parent.split(os.sep) if c]:
            child = os.open(component, DIR_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = child
        # Trip-wire: rmtree(dir_fd=) needs Python 3.11; the fd link pins the
        # opened parent on every version, and rmtree refuses a symlinked name.
        shutil.rmtree(f"/proc/self/fd/{fd}/{name}")
    finally:
        os.close(fd)
