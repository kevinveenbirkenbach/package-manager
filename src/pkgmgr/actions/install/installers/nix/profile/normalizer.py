from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional

from .models import NixProfileEntry


def coerce_index(key: str, entry: Dict[str, Any]) -> Optional[int]:
    """
    Nix JSON schema varies:
      - elements keys might be "0", "1", ...
      - or might be names like "pkgmgr-1"
    Some versions include an explicit index field.
    We try safe options in order.
    """
    k = (key or "").strip()

    # 1) Classic: numeric keys
    if k.isdigit():
        try:
            return int(k)
        except Exception:
            return None

    # 2) Explicit index fields (schema-dependent)
    for field in ("index", "id", "position"):
        v = entry.get(field)
        if isinstance(v, int):
            return v
        if isinstance(v, str) and v.strip().isdigit():
            try:
                return int(v.strip())
            except Exception:
                pass

    # 3) Last resort: extract trailing number from key if it looks like "<name>-<n>"
    m = re.match(r"^.+-(\d+)$", k)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None

    return None


def iter_store_paths(entry: Dict[str, Any]) -> Iterable[str]:
    """
    Yield all possible store paths from a nix profile JSON entry.

    Nix has had schema shifts. We support common variants:
      - "storePaths": ["/nix/store/..", ...]
      - "storePaths": "/nix/store/.."  (rare)
      - "storePath": "/nix/store/.."   (some variants)
      - nested "outputs" dict(s) with store paths (best-effort)
    """
    if not isinstance(entry, dict):
        return

    sp = entry.get("storePaths")
    if isinstance(sp, list):
        for p in sp:
            if isinstance(p, str):
                yield p
    elif isinstance(sp, str):
        yield sp

    sp2 = entry.get("storePath")
    if isinstance(sp2, str):
        yield sp2

    outs = entry.get("outputs")
    if isinstance(outs, dict):
        for _, ov in outs.items():
            if isinstance(ov, dict):
                p = ov.get("storePath")
                if isinstance(p, str):
                    yield p


def normalize_store_path(store_path: str) -> str:
    """
    Normalize store path for matching.
    Currently just strips whitespace; hook for future normalization if needed.
    """
    return (store_path or "").strip()


def normalize_elements(data: Dict[str, Any]) -> List[NixProfileEntry]:
    """
    Converts nix profile list JSON into a list of normalized entries.

    JSON formats observed:
      - {"elements": {"0": {...}, "1": {...}}}
      - {"elements": {"pkgmgr-1": {...}, "pkgmgr-2": {...}}}
    """
    elements = data.get("elements")
    if not isinstance(elements, dict):
        return []

    normalized: List[NixProfileEntry] = []

    for k, entry in elements.items():
        if not isinstance(entry, dict):
            continue

        idx = coerce_index(str(k), entry)
        name = str(entry.get("name", "") or "")
        attr = str(entry.get("attrPath", "") or "")

        store_paths: List[str] = []
        for p in iter_store_paths(entry):
            sp = normalize_store_path(p)
            if sp:
                store_paths.append(sp)

        normalized.append(
            NixProfileEntry(
                key=str(k),
                index=idx,
                name=name,
                attr_path=attr,
                store_paths=store_paths,
            )
        )

    return normalized
