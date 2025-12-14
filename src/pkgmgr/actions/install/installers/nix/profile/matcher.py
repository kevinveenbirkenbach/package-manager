from __future__ import annotations

from typing import List

from .models import NixProfileEntry


def entry_matches_output(entry: NixProfileEntry, output: str) -> bool:
    """
    Heuristic matcher: output is typically a flake output name (e.g. "pkgmgr"),
    and we match against name/attrPath patterns.
    """
    out = (output or "").strip()
    if not out:
        return False

    candidates = [entry.name, entry.attr_path]

    for c in candidates:
        c = (c or "").strip()
        if not c:
            continue

        # Direct match
        if c == out:
            return True

        # AttrPath contains "#<output>"
        if f"#{out}" in c:
            return True

        # AttrPath ends with ".<output>"
        if c.endswith(f".{out}"):
            return True

        # Name pattern "<output>-<n>" (common, e.g. pkgmgr-1)
        if c.startswith(f"{out}-"):
            return True

        # Historical special case: repo is "package-manager" but output is "pkgmgr"
        if out == "pkgmgr" and c.startswith("package-manager-"):
            return True

    return False


def entry_matches_store_path(entry: NixProfileEntry, store_path: str) -> bool:
    needle = (store_path or "").strip()
    if not needle:
        return False
    return any((p or "") == needle for p in entry.store_paths)


def stable_unique_ints(values: List[int]) -> List[int]:
    seen: set[int] = set()
    uniq: List[int] = []
    for v in values:
        if v in seen:
            continue
        uniq.append(v)
        seen.add(v)
    return uniq
