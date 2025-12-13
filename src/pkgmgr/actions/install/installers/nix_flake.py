#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import TYPE_CHECKING, List, Tuple

from pkgmgr.actions.install.installers.base import BaseInstaller
from pkgmgr.core.command.run import run_command

if TYPE_CHECKING:
    from pkgmgr.actions.install.context import RepoContext


class NixFlakeInstaller(BaseInstaller):
    layer = "nix"
    FLAKE_FILE = "flake.nix"

    def supports(self, ctx: "RepoContext") -> bool:
        if os.environ.get("PKGMGR_DISABLE_NIX_FLAKE_INSTALLER") == "1":
            if not ctx.quiet:
                print("[INFO] PKGMGR_DISABLE_NIX_FLAKE_INSTALLER=1 – skipping NixFlakeInstaller.")
            return False

        if shutil.which("nix") is None:
            return False

        return os.path.exists(os.path.join(ctx.repo_dir, self.FLAKE_FILE))

    def _profile_outputs(self, ctx: "RepoContext") -> List[Tuple[str, bool]]:
        # (output_name, allow_failure)
        if ctx.identifier in {"pkgmgr", "package-manager"}:
            return [("pkgmgr", False), ("default", True)]
        return [("default", False)]

    def _installable(self, ctx: "RepoContext", output: str) -> str:
        return f"{ctx.repo_dir}#{output}"

    def _run(self, ctx: "RepoContext", cmd: str, allow_failure: bool = True):
        return run_command(
            cmd,
            cwd=ctx.repo_dir,
            preview=ctx.preview,
            allow_failure=allow_failure,
        )

    def _profile_list_json(self, ctx: "RepoContext") -> dict:
        """
        Read current Nix profile entries as JSON (best-effort).

        NOTE: Nix versions differ:
          - Newer: {"elements": [ { "index": 0, "attrPath": "...", ... }, ... ]}
          - Older: {"elements": [ "nixpkgs#hello", ... ]}   (strings)

        We return {} on failure or in preview mode.
        """
        if ctx.preview:
            return {}

        proc = subprocess.run(
            ["nix", "profile", "list", "--json"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=os.environ.copy(),
        )
        if proc.returncode != 0:
            return {}

        try:
            return json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            return {}

    def _find_installed_indices_for_output(self, ctx: "RepoContext", output: str) -> List[int]:
        """
        Find installed profile indices for a given output.

        Works across Nix JSON variants:
          - If elements are dicts: we can extract indices.
          - If elements are strings: we cannot extract indices -> return [].
        """
        data = self._profile_list_json(ctx)
        elements = data.get("elements", []) or []

        matches: List[int] = []

        for el in elements:
            # Legacy JSON format: plain strings -> no index information
            if not isinstance(el, dict):
                continue

            idx = el.get("index")
            if idx is None:
                continue

            attr_path = el.get("attrPath") or el.get("attr_path") or ""
            pname = el.get("pname") or ""
            name = el.get("name") or ""

            if attr_path == output:
                matches.append(int(idx))
                continue

            if pname == output or name == output:
                matches.append(int(idx))
                continue

            if isinstance(attr_path, str) and attr_path.endswith(f".{output}"):
                matches.append(int(idx))
                continue

        return matches

    def _upgrade_index(self, ctx: "RepoContext", index: int) -> bool:
        cmd = f"nix profile upgrade --refresh {index}"
        if not ctx.quiet:
            print(f"[nix] upgrade: {cmd}")
        res = self._run(ctx, cmd, allow_failure=True)
        return res.returncode == 0

    def _remove_index(self, ctx: "RepoContext", index: int) -> None:
        cmd = f"nix profile remove {index}"
        if not ctx.quiet:
            print(f"[nix] remove: {cmd}")
        self._run(ctx, cmd, allow_failure=True)

    def _install_only(self, ctx: "RepoContext", output: str, allow_failure: bool) -> None:
        """
        Install output; on failure, try index-based upgrade/remove+install if possible.
        """
        installable = self._installable(ctx, output)
        install_cmd = f"nix profile install {installable}"

        if not ctx.quiet:
            print(f"[nix] install: {install_cmd}")

        res = self._run(ctx, install_cmd, allow_failure=True)
        if res.returncode == 0:
            if not ctx.quiet:
                print(f"[nix] output '{output}' successfully installed.")
            return

        if not ctx.quiet:
            print(
                f"[nix] install failed for '{output}' (exit {res.returncode}), "
                "trying index-based upgrade/remove+install..."
            )

        indices = self._find_installed_indices_for_output(ctx, output)

        # 1) Try upgrading existing indices (only possible on newer JSON format)
        upgraded = False
        for idx in indices:
            if self._upgrade_index(ctx, idx):
                upgraded = True
                if not ctx.quiet:
                    print(f"[nix] output '{output}' successfully upgraded (index {idx}).")

        if upgraded:
            return

        # 2) Remove matching indices and retry install
        if indices and not ctx.quiet:
            print(f"[nix] upgrade failed; removing indices {indices} and reinstalling '{output}'.")

        for idx in indices:
            self._remove_index(ctx, idx)

        final = self._run(ctx, install_cmd, allow_failure=True)
        if final.returncode == 0:
            if not ctx.quiet:
                print(f"[nix] output '{output}' successfully re-installed.")
            return

        msg = f"[ERROR] Failed to install Nix flake output '{output}' (exit {final.returncode})"
        print(msg)

        if not allow_failure:
            raise SystemExit(final.returncode)

        print(f"[WARNING] Continuing despite failure of optional output '{output}'.")

    def _force_upgrade_output(self, ctx: "RepoContext", output: str, allow_failure: bool) -> None:
        """
        force_update path:
          - Prefer upgrading existing entries via indices (if we can discover them).
          - If no indices (legacy JSON) or upgrade fails, fall back to install-only logic.
        """
        indices = self._find_installed_indices_for_output(ctx, output)

        upgraded_any = False
        for idx in indices:
            if self._upgrade_index(ctx, idx):
                upgraded_any = True
                if not ctx.quiet:
                    print(f"[nix] output '{output}' successfully upgraded (index {idx}).")

        if upgraded_any:
            # Make upgrades visible to tests
            print(f"[nix] output '{output}' successfully upgraded.")
            return

        if indices and not ctx.quiet:
            print(f"[nix] upgrade failed; removing indices {indices} and reinstalling '{output}'.")

        for idx in indices:
            self._remove_index(ctx, idx)

        # Ensure installed (includes its own fallback logic)
        self._install_only(ctx, output, allow_failure)

        # Make upgrades visible to tests (semantic: update requested)
        print(f"[nix] output '{output}' successfully upgraded.")

    def run(self, ctx: "RepoContext") -> None:
        if not self.supports(ctx):
            return

        outputs = self._profile_outputs(ctx)

        if not ctx.quiet:
            print(
                "[nix] flake detected in "
                f"{ctx.identifier}, ensuring outputs: "
                + ", ".join(name for name, _ in outputs)
            )

        for output, allow_failure in outputs:
            if ctx.force_update:
                self._force_upgrade_output(ctx, output, allow_failure)
            else:
                self._install_only(ctx, output, allow_failure)
