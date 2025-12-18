from __future__ import annotations

from typing import Any, List, TYPE_CHECKING

from .matcher import (
    entry_matches_output,
    entry_matches_store_path,
    stable_unique_ints,
)
from .normalizer import normalize_elements
from .parser import parse_profile_list_json
from .result import extract_stdout_text

if TYPE_CHECKING:
    # Keep these as TYPE_CHECKING-only to avoid runtime import cycles.
    from pkgmgr.actions.install.context import RepoContext
    from pkgmgr.core.command.runner import CommandRunner


class NixProfileInspector:
    """
    Reads and inspects the user's Nix profile list (JSON).

    Public API:
      - list_json()
      - find_installed_indices_for_output()   (legacy; may not work on newer nix)
      - find_indices_by_store_path()          (legacy; may not work on newer nix)
      - find_remove_tokens_for_output()
      - find_remove_tokens_for_store_prefixes()
    """

    def list_json(self, ctx: "RepoContext", runner: "CommandRunner") -> dict[str, Any]:
        res = runner.run(ctx, "nix profile list --json", allow_failure=False)
        raw = extract_stdout_text(res)
        return parse_profile_list_json(raw)

    # ---------------------------------------------------------------------
    # Legacy index helpers (still useful on older nix; newer nix may reject indices)
    # ---------------------------------------------------------------------

    def find_installed_indices_for_output(
        self,
        ctx: "RepoContext",
        runner: "CommandRunner",
        output: str,
    ) -> List[int]:
        data = self.list_json(ctx, runner)
        entries = normalize_elements(data)

        hits: List[int] = []
        for e in entries:
            if e.index is None:
                continue
            if entry_matches_output(e, output):
                hits.append(e.index)

        return stable_unique_ints(hits)

    def find_indices_by_store_path(
        self,
        ctx: "RepoContext",
        runner: "CommandRunner",
        store_path: str,
    ) -> List[int]:
        needle = (store_path or "").strip()
        if not needle:
            return []

        data = self.list_json(ctx, runner)
        entries = normalize_elements(data)

        hits: List[int] = []
        for e in entries:
            if e.index is None:
                continue
            if entry_matches_store_path(e, needle):
                hits.append(e.index)

        return stable_unique_ints(hits)

    # ---------------------------------------------------------------------
    # New token-based helpers (works with newer nix where indices are rejected)
    # ---------------------------------------------------------------------

    def find_remove_tokens_for_output(
        self,
        ctx: "RepoContext",
        runner: "CommandRunner",
        output: str,
    ) -> List[str]:
        """
        Returns profile remove tokens to remove entries matching a given output.

        We always include the raw output token first because nix itself suggests:
          nix profile remove pkgmgr
        """
        out = (output or "").strip()
        if not out:
            return []

        data = self.list_json(ctx, runner)
        entries = normalize_elements(data)

        tokens: List[str] = [
            out
        ]  # critical: matches nix's own suggestion for conflicts

        for e in entries:
            if entry_matches_output(e, out):
                # Prefer removing by key/name (non-index) when possible.
                # New nix rejects numeric indices; these tokens are safer.
                k = (e.key or "").strip()
                n = (e.name or "").strip()

                if k and not k.isdigit():
                    tokens.append(k)
                elif n and not n.isdigit():
                    tokens.append(n)

        # stable unique preserving order
        seen: set[str] = set()
        uniq: List[str] = []
        for t in tokens:
            if t and t not in seen:
                uniq.append(t)
                seen.add(t)
        return uniq

    def find_remove_tokens_for_store_prefixes(
        self,
        ctx: "RepoContext",
        runner: "CommandRunner",
        prefixes: List[str],
    ) -> List[str]:
        """
        Returns remove tokens for entries whose store path matches any prefix.
        """
        prefixes = [(p or "").strip() for p in (prefixes or []) if p]
        prefixes = [p for p in prefixes if p]
        if not prefixes:
            return []

        data = self.list_json(ctx, runner)
        entries = normalize_elements(data)

        tokens: List[str] = []
        for e in entries:
            if not e.store_paths:
                continue
            if any(sp == p for sp in e.store_paths for p in prefixes):
                k = (e.key or "").strip()
                n = (e.name or "").strip()
                if k and not k.isdigit():
                    tokens.append(k)
                elif n and not n.isdigit():
                    tokens.append(n)

        seen: set[str] = set()
        uniq: List[str] = []
        for t in tokens:
            if t and t not in seen:
                uniq.append(t)
                seen.add(t)
        return uniq
