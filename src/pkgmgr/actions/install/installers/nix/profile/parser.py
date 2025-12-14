from __future__ import annotations

import json
from typing import Any, Dict


def parse_profile_list_json(raw: str) -> Dict[str, Any]:
    """
    Parse JSON output from `nix profile list --json`.

    Raises SystemExit with a helpful excerpt on parse failure.
    """
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        excerpt = (raw or "")[:5000]
        raise SystemExit(
            f"[nix] Failed to parse `nix profile list --json`: {e}\n{excerpt}"
        ) from e
