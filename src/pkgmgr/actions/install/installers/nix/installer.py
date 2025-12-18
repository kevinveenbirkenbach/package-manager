from __future__ import annotations

import os
import shutil
from typing import TYPE_CHECKING, List, Tuple

from pkgmgr.actions.install.installers.base import BaseInstaller

from .conflicts import NixConflictResolver
from .profile import NixProfileInspector
from .retry import GitHubRateLimitRetry, RetryPolicy
from .runner import CommandRunner

if TYPE_CHECKING:
    from pkgmgr.actions.install.context import RepoContext


class NixFlakeInstaller(BaseInstaller):
    layer = "nix"
    FLAKE_FILE = "flake.nix"

    def __init__(self, policy: RetryPolicy | None = None) -> None:
        self._runner = CommandRunner()
        self._retry = GitHubRateLimitRetry(policy=policy)
        self._profile = NixProfileInspector()
        self._conflicts = NixConflictResolver(self._runner, self._retry, self._profile)

        # Newer nix rejects numeric indices; we learn this at runtime and cache the decision.
        self._indices_supported: bool | None = None

    def supports(self, ctx: "RepoContext") -> bool:
        if os.environ.get("PKGMGR_DISABLE_NIX_FLAKE_INSTALLER") == "1":
            if not ctx.quiet:
                print(
                    "[INFO] PKGMGR_DISABLE_NIX_FLAKE_INSTALLER=1 – "
                    "skipping NixFlakeInstaller."
                )
            return False

        if shutil.which("nix") is None:
            return False

        return os.path.exists(os.path.join(ctx.repo_dir, self.FLAKE_FILE))

    def _profile_outputs(self, ctx: "RepoContext") -> List[Tuple[str, bool]]:
        # (output_name, allow_failure)
        if ctx.identifier in {"pkgmgr", "package-manager"}:
            return [("pkgmgr", False), ("default", True)]
        return [("default", False)]

    def run(self, ctx: "RepoContext") -> None:
        if not self.supports(ctx):
            return

        outputs = self._profile_outputs(ctx)

        if not ctx.quiet:
            msg = (
                "[nix] flake detected in "
                f"{ctx.identifier}, ensuring outputs: "
                + ", ".join(name for name, _ in outputs)
            )
            print(msg)

        for output, allow_failure in outputs:
            if ctx.force_update:
                self._force_upgrade_output(ctx, output, allow_failure)
            else:
                self._install_only(ctx, output, allow_failure)

    def _installable(self, ctx: "RepoContext", output: str) -> str:
        return f"{ctx.repo_dir}#{output}"

    # ---------------------------------------------------------------------
    # Core install path
    # ---------------------------------------------------------------------

    def _install_only(
        self, ctx: "RepoContext", output: str, allow_failure: bool
    ) -> None:
        install_cmd = f"nix profile install {self._installable(ctx, output)}"

        if not ctx.quiet:
            print(f"[nix] install: {install_cmd}")

        res = self._retry.run_with_retry(ctx, self._runner, install_cmd)
        if res.returncode == 0:
            if not ctx.quiet:
                print(f"[nix] output '{output}' successfully installed.")
            return

        # Conflict resolver first (handles the common “existing package already provides file” case)
        if self._conflicts.resolve(
            ctx,
            install_cmd,
            res.stdout,
            res.stderr,
            output=output,
        ):
            if not ctx.quiet:
                print(
                    f"[nix] output '{output}' successfully installed after conflict cleanup."
                )
            return

        if not ctx.quiet:
            print(
                f"[nix] install failed for '{output}' (exit {res.returncode}), "
                "trying upgrade/remove+install..."
            )

        # If indices are supported, try legacy index-upgrade path.
        if self._indices_supported is not False:
            indices = self._profile.find_installed_indices_for_output(
                ctx, self._runner, output
            )

            upgraded = False
            for idx in indices:
                if self._upgrade_index(ctx, idx):
                    upgraded = True
                    if not ctx.quiet:
                        print(
                            f"[nix] output '{output}' successfully upgraded (index {idx})."
                        )

            if upgraded:
                return

            if indices and not ctx.quiet:
                print(
                    f"[nix] upgrade failed; removing indices {indices} and reinstalling '{output}'."
                )

            for idx in indices:
                self._remove_index(ctx, idx)

            # If we learned indices are unsupported, immediately fall back below
            if self._indices_supported is False:
                self._remove_tokens_for_output(ctx, output)

        else:
            # indices explicitly unsupported
            self._remove_tokens_for_output(ctx, output)

        final = self._runner.run(ctx, install_cmd, allow_failure=True)
        if final.returncode == 0:
            if not ctx.quiet:
                print(f"[nix] output '{output}' successfully re-installed.")
            return

        print(
            f"[ERROR] Failed to install Nix flake output '{output}' (exit {final.returncode})"
        )
        if not allow_failure:
            raise SystemExit(final.returncode)

        print(f"[WARNING] Continuing despite failure of optional output '{output}'.")

    # ---------------------------------------------------------------------
    # force_update path
    # ---------------------------------------------------------------------

    def _force_upgrade_output(
        self, ctx: "RepoContext", output: str, allow_failure: bool
    ) -> None:
        # Prefer token path if indices unsupported (new nix)
        if self._indices_supported is False:
            self._remove_tokens_for_output(ctx, output)
            self._install_only(ctx, output, allow_failure)
            if not ctx.quiet:
                print(f"[nix] output '{output}' successfully upgraded.")
            return

        indices = self._profile.find_installed_indices_for_output(
            ctx, self._runner, output
        )

        upgraded_any = False
        for idx in indices:
            if self._upgrade_index(ctx, idx):
                upgraded_any = True
                if not ctx.quiet:
                    print(
                        f"[nix] output '{output}' successfully upgraded (index {idx})."
                    )

        if upgraded_any:
            if not ctx.quiet:
                print(f"[nix] output '{output}' successfully upgraded.")
            return

        if indices and not ctx.quiet:
            print(
                f"[nix] upgrade failed; removing indices {indices} and reinstalling '{output}'."
            )

        for idx in indices:
            self._remove_index(ctx, idx)

        # If we learned indices are unsupported, also remove by token to actually clear conflicts
        if self._indices_supported is False:
            self._remove_tokens_for_output(ctx, output)

        self._install_only(ctx, output, allow_failure)

        if not ctx.quiet:
            print(f"[nix] output '{output}' successfully upgraded.")

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------

    def _stderr_says_indices_unsupported(self, stderr: str) -> bool:
        s = (stderr or "").lower()
        return "no longer supports indices" in s or "does not support indices" in s

    def _upgrade_index(self, ctx: "RepoContext", idx: int) -> bool:
        cmd = f"nix profile upgrade --refresh {idx}"
        res = self._runner.run(ctx, cmd, allow_failure=True)

        if self._stderr_says_indices_unsupported(getattr(res, "stderr", "")):
            self._indices_supported = False
            return False

        if self._indices_supported is None:
            self._indices_supported = True

        return res.returncode == 0

    def _remove_index(self, ctx: "RepoContext", idx: int) -> None:
        res = self._runner.run(ctx, f"nix profile remove {idx}", allow_failure=True)

        if self._stderr_says_indices_unsupported(getattr(res, "stderr", "")):
            self._indices_supported = False

        if self._indices_supported is None:
            self._indices_supported = True

    def _remove_tokens_for_output(self, ctx: "RepoContext", output: str) -> None:
        tokens = self._profile.find_remove_tokens_for_output(ctx, self._runner, output)
        if not tokens:
            return

        if not ctx.quiet:
            print(
                f"[nix] indices unsupported; removing by token(s): {', '.join(tokens)}"
            )

        for t in tokens:
            self._runner.run(ctx, f"nix profile remove {t}", allow_failure=True)
