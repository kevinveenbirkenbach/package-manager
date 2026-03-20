from __future__ import annotations

import subprocess

from ..errors import GitNotRepositoryError, GitQueryError


class GitLatestSigningKeyQueryError(GitQueryError):
    """Raised when querying the latest commit signing key fails."""


def _is_not_repository(stderr: str) -> bool:
    return "not a git repository" in (stderr or "").lower()


def _looks_like_gpg_runtime_error(stderr: str) -> bool:
    lowered = (stderr or "").lower()
    markers = (
        "cannot run gpg",
        "can't check signature",
        "no public key",
        "failed to create temporary file",
        "can't connect to the keyboxd",
        "error opening key db",
        "gpg failed",
        "no such file or directory",
    )
    return any(marker in lowered for marker in markers)


def get_latest_signing_key(*, cwd: str = ".") -> str:
    """
    Return the GPG signing key ID of the latest commit, via:

      git log -1 --format=%GK

    Returns:
      The key id string (may be empty if commit is not signed).
    """
    cmd = ["git", "log", "-1", "--format=%GK"]
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        raise GitLatestSigningKeyQueryError(
            "Failed to query latest signing key.\n"
            f"Command: {' '.join(cmd)}\n"
            f"Reason: {exc}"
        ) from exc

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()

    if result.returncode != 0:
        if _is_not_repository(stderr):
            raise GitNotRepositoryError(
                f"Not a git repository: {cwd!r}\n"
                f"Command: {' '.join(cmd)}\n"
                f"STDERR:\n{stderr}"
            )
        raise GitLatestSigningKeyQueryError(
            "Failed to query latest signing key.\n"
            f"Command: {' '.join(cmd)}\n"
            f"Exit code: {result.returncode}\n"
            f"STDOUT:\n{stdout}\n"
            f"STDERR:\n{stderr}"
        )

    if not stdout and stderr and _looks_like_gpg_runtime_error(stderr):
        raise GitLatestSigningKeyQueryError(
            "Failed to query latest signing key.\n"
            f"Command: {' '.join(cmd)}\n"
            f"STDERR:\n{stderr}"
        )

    return stdout
