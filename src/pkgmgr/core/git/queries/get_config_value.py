from __future__ import annotations

from typing import Optional

from ..errors import GitRunError
from ..run import run


def _is_missing_key_error(exc: GitRunError) -> bool:
    msg = str(exc).lower()

    # Ensure we only swallow the expected case for THIS command.
    if "git config --get" not in msg:
        return False

    # 'git config --get' returns exit code 1 when the key is not set.
    return "exit code: 1" in msg


def get_config_value(key: str, *, cwd: str = ".") -> Optional[str]:
    """
    Return a value from `git config --get <key>`, or None if not set.

    We keep core.git.run() strict (check=True) and interpret the known
    'not set' exit-code case here.
    """
    try:
        output = run(["config", "--get", key], cwd=cwd)
    except GitRunError as exc:
        if _is_missing_key_error(exc):
            return None
        raise

    output = output.strip()
    return output or None
