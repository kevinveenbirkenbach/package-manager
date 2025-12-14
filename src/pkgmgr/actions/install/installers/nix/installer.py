# src/pkgmgr/actions/install/installers/nix/installer.py
from __future__ import annotations

import os
import shutil
from typing import List, Tuple

from pkgmgr.actions.install.installers.base import BaseInstaller

from .profile import NixProfileInspector
from .retry import GitHubRateLimitRetry, RetryPolicy
from .runner import CommandRunner


class NixFlakeInstaller(BaseInstaller):
    layer = "nix"
    FLAKE_FILE = "flake.nix"

    def __init__(self, policy: RetryPolicy | None = None) -> None:
        self._runner = CommandRunner()
        self._retry = GitHubRateLimitRetry(policy=policy)
        self._profile = NixProfileInspector()

    # ------------------------------------------------------------------ #
    # Compatibility: supports()
    # ------------------------------------------------------------------ #

    def supports(self, ctx: "RepoContext") -> bool:
        if os.environ.get("PKGMGR_DISABLE_NIX_FLAKE_INSTALLER") == "1":
            if not ctx.quiet:
                print("[INFO] PKGMGR_DISABLE_NIX_FLAKE_INSTALLER=1 – skipping NixFlakeInstaller.")
            return False

        if shutil.which("nix") is None:
            return False

        return os.path.exists(os.path.join(ctx.repo_dir, self.FLAKE_FILE))

    # ------------------------------------------------------------------ #
    # Compatibility: output selection
    # ------------------------------------------------------------------ #

    def _profile_outputs(self, ctx: "RepoContext") -> List[Tuple[str, bool]]:
        # (output_name, allow_failure)
        if ctx.identifier in {"pkgmgr", "package-manager"}:
            return [("pkgmgr", False), ("default", True)]
        return [("default", False)]

    # ------------------------------------------------------------------ #
    # Compatibility: run()
    # ------------------------------------------------------------------ #

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

    # ------------------------------------------------------------------ #
    # Core logic (unchanged semantics)
    # ------------------------------------------------------------------ #

    def _installable(self, ctx: "RepoContext", output: str) -> str:
        return f"{ctx.repo_dir}#{output}"

    def _install_only(self, ctx: "RepoContext", output: str, allow_failure: bool) -> None:
        install_cmd = f"nix profile install {self._installable(ctx, output)}"

        if not ctx.quiet:
            print(f"[nix] install: {install_cmd}")

        res = self._retry.run_with_retry(ctx, self._runner, install_cmd)

        if res.returncode == 0:
            if not ctx.quiet:
                print(f"[nix] output '{output}' successfully installed.")
            return

        if not ctx.quiet:
            print(
                f"[nix] install failed for '{output}' (exit {res.returncode}), "
                "trying index-based upgrade/remove+install..."
            )

        indices = self._profile.find_installed_indices_for_output(ctx, self._runner, output)

        upgraded = False
        for idx in indices:
            if self._upgrade_index(ctx, idx):
                upgraded = True
                if not ctx.quiet:
                    print(f"[nix] output '{output}' successfully upgraded (index {idx}).")

        if upgraded:
            return

        if indices and not ctx.quiet:
            print(f"[nix] upgrade failed; removing indices {indices} and reinstalling '{output}'.")

        for idx in indices:
            self._remove_index(ctx, idx)

        final = self._runner.run(ctx, install_cmd, allow_failure=True)
        if final.returncode == 0:
            if not ctx.quiet:
                print(f"[nix] output '{output}' successfully re-installed.")
            return

        print(f"[ERROR] Failed to install Nix flake output '{output}' (exit {final.returncode})")

        if not allow_failure:
            raise SystemExit(final.returncode)

        print(f"[WARNING] Continuing despite failure of optional output '{output}'.")

    # ------------------------------------------------------------------ #
    # force_update path (unchanged semantics)
    # ------------------------------------------------------------------ #

    def _force_upgrade_output(self, ctx: "RepoContext", output: str, allow_failure: bool) -> None:
        indices = self._profile.find_installed_indices_for_output(ctx, self._runner, output)

        upgraded_any = False
        for idx in indices:
            if self._upgrade_index(ctx, idx):
                upgraded_any = True
                if not ctx.quiet:
                    print(f"[nix] output '{output}' successfully upgraded (index {idx}).")

        if upgraded_any:
            print(f"[nix] output '{output}' successfully upgraded.")
            return

        if indices and not ctx.quiet:
            print(f"[nix] upgrade failed; removing indices {indices} and reinstalling '{output}'.")

        for idx in indices:
            self._remove_index(ctx, idx)

        self._install_only(ctx, output, allow_failure)

        print(f"[nix] output '{output}' successfully upgraded.")

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _upgrade_index(self, ctx: "RepoContext", idx: int) -> bool:
        res = self._runner.run(ctx, f"nix profile upgrade --refresh {idx}", allow_failure=True)
        return res.returncode == 0

    def _remove_index(self, ctx: "RepoContext", idx: int) -> None:
        self._runner.run(ctx, f"nix profile remove {idx}", allow_failure=True)
