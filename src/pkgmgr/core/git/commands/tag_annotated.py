from __future__ import annotations

from ..errors import GitRunError, GitCommandError
from ..run import run


class GitTagAnnotatedError(GitCommandError):
    """Raised when creating an annotated tag fails."""


def tag_annotated(
    tag: str,
    message: str,
    *,
    cwd: str = ".",
    preview: bool = False,
) -> None:
    """
    Create an annotated tag.

    Equivalent to:
      git tag -a <tag> -m "<message>"
    """
    try:
        run(["tag", "-a", tag, "-m", message], cwd=cwd, preview=preview)
    except GitRunError as exc:
        raise GitTagAnnotatedError(
            f"Failed to create annotated tag {tag!r}.",
            cwd=cwd,
        ) from exc
