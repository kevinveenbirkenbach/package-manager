# src/pkgmgr/actions/mirror/remote_check.py
from __future__ import annotations

from typing import Tuple

from pkgmgr.core.git import GitError, run_git


def probe_mirror(url: str, repo_dir: str) -> Tuple[bool, str]:
    """
    Probe a remote mirror URL using `git ls-remote`.

    Returns:
      (True, "") on success,
      (False, error_message) on failure.
    """
    try:
        run_git(["ls-remote", url], cwd=repo_dir)
        return True, ""
    except GitError as exc:
        return False, str(exc)
