from __future__ import annotations

from typing import Any


def extract_stdout_text(result: Any) -> str:
    """
    Normalize different runner return types to a stdout string.

    Supported patterns:
      - result is str -> returned as-is
      - result is bytes/bytearray -> decoded UTF-8 (replace errors)
      - result has `.stdout` (str or bytes) -> used
      - fallback: str(result)
    """
    if isinstance(result, str):
        return result

    if isinstance(result, (bytes, bytearray)):
        return bytes(result).decode("utf-8", errors="replace")

    stdout = getattr(result, "stdout", None)
    if isinstance(stdout, str):
        return stdout
    if isinstance(stdout, (bytes, bytearray)):
        return bytes(stdout).decode("utf-8", errors="replace")

    return str(result)
