from __future__ import annotations

import re
from typing import TYPE_CHECKING, List, Tuple

from .runner import CommandRunner

if TYPE_CHECKING:
    from pkgmgr.actions.install.context import RepoContext


class NixProfileListReader:
    def __init__(self, runner: CommandRunner) -> None:
        self._runner = runner

    @staticmethod
    def _store_prefix(path: str) -> str:
        raw = (path or "").strip()
        m = re.match(r"^(/nix/store/[0-9a-z]{32}-[^/ \t]+)", raw)
        return m.group(1) if m else raw

    def entries(self, ctx: "RepoContext") -> List[Tuple[int, str]]:
        res = self._runner.run(ctx, "nix profile list", allow_failure=True)
        if res.returncode != 0:
            return []

        entries: List[Tuple[int, str]] = []
        pat = re.compile(
            r"^\s*(\d+)\s+.*?(/nix/store/[0-9a-z]{32}-[^/ \t]+)",
            re.MULTILINE,
        )

        for m in pat.finditer(res.stdout or ""):
            idx_s = m.group(1)
            sp = m.group(2)
            try:
                idx = int(idx_s)
            except Exception:
                continue
            entries.append((idx, self._store_prefix(sp)))

        seen: set[int] = set()
        uniq: List[Tuple[int, str]] = []
        for idx, sp in entries:
            if idx not in seen:
                seen.add(idx)
                uniq.append((idx, sp))

        return uniq

    def indices_matching_store_prefixes(
        self, ctx: "RepoContext", prefixes: List[str]
    ) -> List[int]:
        prefixes = [self._store_prefix(p) for p in prefixes if p]
        prefixes = [p for p in prefixes if p]
        if not prefixes:
            return []

        hits: List[int] = []
        for idx, sp in self.entries(ctx):
            if any(sp == p for p in prefixes):
                hits.append(idx)

        seen: set[int] = set()
        uniq: List[int] = []
        for i in hits:
            if i not in seen:
                seen.add(i)
                uniq.append(i)

        return uniq
