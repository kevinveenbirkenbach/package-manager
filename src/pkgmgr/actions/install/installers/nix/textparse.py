from __future__ import annotations

import re
from typing import List


class NixConflictTextParser:
    @staticmethod
    def _store_prefix(path: str) -> str:
        raw = (path or "").strip()
        m = re.match(r"^(/nix/store/[0-9a-z]{32}-[^/ \t]+)", raw)
        return m.group(1) if m else raw

    def remove_tokens(self, text: str) -> List[str]:
        pat = re.compile(
            r"^\s*nix profile remove\s+([^\s'\"`]+|'[^']+'|\"[^\"]+\")\s*$",
            re.MULTILINE,
        )

        tokens: List[str] = []
        for m in pat.finditer(text or ""):
            t = (m.group(1) or "").strip()
            if (t.startswith("'") and t.endswith("'")) or (
                t.startswith('"') and t.endswith('"')
            ):
                t = t[1:-1]
            if t:
                tokens.append(t)

        seen: set[str] = set()
        uniq: List[str] = []
        for t in tokens:
            if t not in seen:
                seen.add(t)
                uniq.append(t)

        return uniq

    def existing_store_prefixes(self, text: str) -> List[str]:
        lines = (text or "").splitlines()
        prefixes: List[str] = []

        in_existing = False
        in_new = False

        store_pat = re.compile(r"^\s*(/nix/store/[0-9a-z]{32}-[^ \t]+)")

        for raw in lines:
            line = raw.strip()

            if "An existing package already provides the following file" in line:
                in_existing = True
                in_new = False
                continue

            if "This is the conflicting file from the new package" in line:
                in_existing = False
                in_new = True
                continue

            if in_existing:
                m = store_pat.match(raw)
                if m:
                    prefixes.append(m.group(1))
                    continue

            _ = in_new

        norm = [self._store_prefix(p) for p in prefixes if p]

        seen: set[str] = set()
        uniq: List[str] = []
        for p in norm:
            if p and p not in seen:
                seen.add(p)
                uniq.append(p)

        return uniq
