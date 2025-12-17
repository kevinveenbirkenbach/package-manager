from __future__ import annotations

from ..errors import GitRunError, GitCommandError
from ..run import run


class GitTagForceAnnotatedError(GitCommandError):
    """Raised when forcing an annotated tag fails."""


def tag_force_annotated(
    name: str,
    target: str,
    message: str,
    *,
    cwd: str = ".",
    preview: bool = False,
) -> None:
    """
    Force-create an annotated tag pointing at a given target.

    Equivalent to:
      git tag -f -a <name> <target> -m "<message>"
    """
    try:
        run(["tag", "-f", "-a", name, target, "-m", message], cwd=cwd, preview=preview)
    except GitRunError as exc:
        raise GitTagForceAnnotatedError(
            f"Failed to force annotated tag {name!r} at {target!r}.",
            cwd=cwd,
        ) from exc
