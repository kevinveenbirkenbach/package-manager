from __future__ import annotations

from typing import List

from ..errors import GitRunError, GitCommandError
from ..run import run


class GitPushArgsError(GitCommandError):
    """Raised when `git push` with arbitrary args fails."""


def push_args(
    args: List[str] | None = None,
    *,
    cwd: str = ".",
    preview: bool = False,
) -> None:
    """
    Execute `git push` with caller-provided arguments.

    Examples:
      []                          -> git push
      ["--force"]                 -> git push --force
      ["origin", "main"]          -> git push origin main
      ["-u", "origin", "feature"] -> git push -u origin feature
    """
    extra = args or []
    try:
        run(["push", *extra], cwd=cwd, preview=preview)
    except GitRunError as exc:
        details = getattr(exc, "output", None) or getattr(exc, "stderr", None) or ""
        raise GitPushArgsError(
            (
                f"Failed to run `git push` with args={extra!r} "
                f"in cwd={cwd!r}.\n{details}"
            ).rstrip(),
            cwd=cwd,
        ) from exc
