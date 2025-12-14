from __future__ import annotations

import json
from typing import Any, List, TYPE_CHECKING


if TYPE_CHECKING:
    from pkgmgr.actions.install.context import RepoContext
    from .runner import CommandRunner
 
class NixProfileInspector:
    """
    Reads and interprets `nix profile list --json` and provides helpers for
    finding indices matching a given output name.
    """

    def find_installed_indices_for_output(self, ctx: "RepoContext", runner: "CommandRunner", output: str) -> List[int]:
        res = runner.run(ctx, "nix profile list --json", allow_failure=True)
        if res.returncode != 0:
            return []

        try:
            data = json.loads(res.stdout or "{}")
        except json.JSONDecodeError:
            return []

        indices: List[int] = []

        elements = data.get("elements")
        if isinstance(elements, dict):
            for idx_str, elem in elements.items():
                try:
                    idx = int(idx_str)
                except (TypeError, ValueError):
                    continue
                if self._element_matches_output(elem, output):
                    indices.append(idx)
            return sorted(indices)

        if isinstance(elements, list):
            for elem in elements:
                idx = elem.get("index") if isinstance(elem, dict) else None
                if isinstance(idx, int) and self._element_matches_output(elem, output):
                    indices.append(idx)
            return sorted(indices)

        return []

    @staticmethod
    def element_matches_output(elem: Any, output: str) -> bool:
        return NixProfileInspector._element_matches_output(elem, output)

    @staticmethod
    def _element_matches_output(elem: Any, output: str) -> bool:
        out = (output or "").strip()
        if not out or not isinstance(elem, dict):
            return False

        candidates: List[str] = []
        for k in ("attrPath", "originalUrl", "url", "storePath", "name"):
            v = elem.get(k)
            if isinstance(v, str) and v:
                candidates.append(v)

        for c in candidates:
            if c == out:
                return True
            if f"#{out}" in c:
                return True

        return False
