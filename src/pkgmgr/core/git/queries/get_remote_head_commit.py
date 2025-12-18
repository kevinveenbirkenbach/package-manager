from __future__ import annotations

from ..errors import GitQueryError, GitRunError
from ..run import run


class GitRemoteHeadCommitQueryError(GitQueryError):
    """Raised when querying the remote HEAD commit fails."""


def get_remote_head_commit(
    *,
    remote: str = "origin",
    ref: str = "HEAD",
    cwd: str = ".",
) -> str:
    """
    Return the commit hash for <remote> <ref> via:

      git ls-remote <remote> <ref>

    Returns:
      The commit hash string (may be empty if remote/ref yields no output).
    """
    try:
        out = run(["ls-remote", remote, ref], cwd=cwd).strip()
    except GitRunError as exc:
        raise GitRemoteHeadCommitQueryError(
            f"Failed to query remote head commit for {remote!r} {ref!r}.",
        ) from exc

    # minimal parsing: first token is the hash
    return out.split()[0].strip() if out else ""
