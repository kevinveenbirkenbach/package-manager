from __future__ import annotations

from ..errors import GitRunError
from ..run import run

FILTER_CONFIG = r"^filter\."
LOCAL_SCOPES = ("local", "worktree")


def local_config(path: str, pattern: str) -> list[str]:
    """
    List the config keys matching pattern that the repository itself sets.

    Args:
        path: any directory inside the repository.
        pattern: `git config --get-regexp` pattern over the canonical key names.

    Returns:
        Each matching key set in the local or worktree scope, in config order;
        global values never count, system config is not read.
    """
    try:
        out = run(
            ["config", "--show-scope", "--get-regexp", pattern], cwd=path, scan=True
        )
    except GitRunError as exc:
        if exc.returncode == 1:
            return []
        raise
    keys: list[str] = []
    for line in out.splitlines():
        scope, _, rest = line.partition("\t")
        if scope in LOCAL_SCOPES:
            keys.append(rest.split(" ", 1)[0])
    return keys
