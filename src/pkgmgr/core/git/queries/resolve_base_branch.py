from __future__ import annotations

from ..errors import GitQueryError, GitRunError
from ..run import run


class GitBaseBranchNotFoundError(GitQueryError):
    """Raised when neither preferred nor fallback base branch exists."""


def _is_branch_missing_error(exc: GitRunError) -> bool:
    """
    Heuristic: Detect errors that indicate the branch/ref does not exist.

    We intentionally *do not* swallow other errors like:
      - not a git repository
      - permission issues
      - corrupted repository
    """
    msg = str(exc).lower()

    # Common git messages when verifying a non-existing ref/branch.
    patterns = [
        "needed a single revision",
        "unknown revision or path not in the working tree",
        "not a valid object name",
        "ambiguous argument",
        "bad revision",
        "fatal: invalid object name",
        "fatal: ambiguous argument",
    ]

    return any(p in msg for p in patterns)


def resolve_base_branch(
    preferred: str = "main",
    fallback: str = "master",
    cwd: str = ".",
) -> str:
    """
    Resolve the base branch to use.

    Try `preferred` first (default: main),
    fall back to `fallback` (default: master).

    Raises GitBaseBranchNotFoundError if neither exists.
    Raises GitRunError for other git failures (e.g., not a git repository).
    """
    last_missing_error: GitRunError | None = None

    for candidate in (preferred, fallback):
        try:
            run(["rev-parse", "--verify", candidate], cwd=cwd)
            return candidate
        except GitRunError as exc:
            if _is_branch_missing_error(exc):
                last_missing_error = exc
                continue
            raise  # anything else is a real problem -> bubble up

    # Both candidates missing -> raise specific error
    raise GitBaseBranchNotFoundError(
        f"Neither {preferred!r} nor {fallback!r} exist in this repository."
    ) from last_missing_error
