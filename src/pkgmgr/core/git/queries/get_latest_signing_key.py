from __future__ import annotations

from ..errors import GitQueryError, GitRunError
from ..run import run


class GitLatestSigningKeyQueryError(GitQueryError):
    """Raised when querying the latest commit signing key fails."""


def get_latest_signing_key(*, cwd: str = ".") -> str:
    """
    Return the GPG signing key ID of the latest commit, via:

      git log -1 --format=%GK

    Returns:
      The key id string (may be empty if commit is not signed).
    """
    try:
        return run(["log", "-1", "--format=%GK"], cwd=cwd).strip()
    except GitRunError as exc:
        raise GitLatestSigningKeyQueryError(
            "Failed to query latest signing key.",
        ) from exc
