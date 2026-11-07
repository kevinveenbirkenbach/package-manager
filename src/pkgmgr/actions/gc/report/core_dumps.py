from __future__ import annotations

import os

from .walk import BLOCK

ELF_MAGIC = b"\x7fELF"
ELF_HEADER = 18
ET_CORE = 4
BYTE_ORDER = {1: "little", 2: "big"}


def is_core_dump(path: str) -> bool:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except OSError:
        return False
    try:
        head = os.read(fd, ELF_HEADER)
    except OSError:
        return False
    finally:
        os.close(fd)
    order = BYTE_ORDER.get(head[5]) if len(head) == ELF_HEADER else None
    return (
        head[:4] == ELF_MAGIC
        and order is not None
        and int.from_bytes(head[16:18], order) == ET_CORE
    )


def core_dumps(candidates: list[str]) -> list[dict]:
    """
    Keep the candidates whose ELF header says ET_CORE.

    Args:
        candidates: paths of regular files named like core dumps.

    Returns:
        One entry per dump with its allocated and apparent size and mtime,
        biggest first.
    """
    dumps: dict[str, dict] = {}
    for path in candidates:
        real = os.path.realpath(path)
        if real in dumps or not is_core_dump(path):
            continue
        try:
            st = os.lstat(path)
        except OSError:
            continue
        dumps[real] = {
            "path": path,
            "size_bytes": st.st_blocks * BLOCK,
            "apparent_bytes": st.st_size,
            "mtime": st.st_mtime,
        }
    return sorted(dumps.values(), key=lambda d: (-d["size_bytes"], d["path"]))
