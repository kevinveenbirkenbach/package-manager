from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Union

from ..errors import GitCommandError, GitRunError
from ..run import run


class GitAddError(GitCommandError):
    """Raised when `git add` fails."""


PathLike = Union[str, Sequence[str], Iterable[str]]


def _normalize_paths(paths: PathLike) -> list[str]:
    if isinstance(paths, str):
        return [paths]
    return [p for p in paths]


def add(
    paths: PathLike,
    *,
    cwd: str = ".",
    preview: bool = False,
) -> None:
    """
    Stage one or multiple paths.

    Equivalent to:
      git add <path...>
    """
    normalized = _normalize_paths(paths)
    if not normalized:
        return

    try:
        run(["add", *normalized], cwd=cwd, preview=preview)
    except GitRunError as exc:
        raise GitAddError(
            f"Failed to add paths to staging area: {normalized!r}.",
            cwd=cwd,
        ) from exc
