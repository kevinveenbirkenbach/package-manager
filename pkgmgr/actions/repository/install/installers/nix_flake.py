#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer for Nix flakes.

If a repository contains flake.nix and the 'nix' command is available, this
installer will try to install profile outputs from the flake.

Behavior:
  - If flake.nix is present and `nix` exists on PATH:
      * First remove any existing `package-manager` profile entry (best-effort).
      * Then install the flake outputs (`pkgmgr`, `default`) via `nix profile install`.
  - Failure installing `pkgmgr` is treated as fatal.
  - Failure installing `default` is logged as an error/warning but does not abort.

Special handling for dev shells / CI:
  - If IN_NIX_SHELL is set (e.g. inside `nix develop`), the installer is
    disabled. In that environment the flake outputs are already provided
    by the dev shell and we must not touch the user profile.
  - If PKGMGR_DISABLE_NIX_FLAKE_INSTALLER=1 is set, the installer is
    globally disabled (useful for CI or debugging).
"""

import os
import shutil
from typing import TYPE_CHECKING

from pkgmgr.actions.repository.install.installers.base import BaseInstaller
from pkgmgr.core.command.run import run_command

if TYPE_CHECKING:
    from pkgmgr.actions.repository.install.context import RepoContext
    from pkgmgr.actions.repository.install import InstallContext


class NixFlakeInstaller(BaseInstaller):
    """Install Nix flake profiles for repositories that define flake.nix."""

    # Logical layer name, used by capability matchers.
    layer = "nix"

    FLAKE_FILE = "flake.nix"
    PROFILE_NAME = "package-manager"

    def _in_nix_shell(self) -> bool:
        """
        Return True if we appear to be running inside a Nix dev shell.

        Nix sets IN_NIX_SHELL in `nix develop` environments. In that case
        the flake outputs are already available, and touching the user
        profile (nix profile install/remove) is undesirable.
        """
        return bool(os.environ.get("IN_NIX_SHELL"))

    def supports(self, ctx: "RepoContext") -> bool:
        """
        Only support repositories that:
          - Are NOT inside a Nix dev shell (IN_NIX_SHELL unset),
          - Are NOT explicitly disabled via PKGMGR_DISABLE_NIX_FLAKE_INSTALLER=1,
          - Have a flake.nix,
          - And have the `nix` command available.
        """
        # 1) Skip when running inside a dev shell – flake is already active.
        if self._in_nix_shell():
            print(
                "[INFO] IN_NIX_SHELL detected; skipping NixFlakeInstaller. "
                "Flake outputs are provided by the development shell."
            )
            return False

        # 2) Optional global kill-switch for CI or debugging.
        if os.environ.get("PKGMGR_DISABLE_NIX_FLAKE_INSTALLER") == "1":
            print(
                "[INFO] PKGMGR_DISABLE_NIX_FLAKE_INSTALLER=1 – "
                "NixFlakeInstaller is disabled."
            )
            return False

        # 3) Nix must be available.
        if shutil.which("nix") is None:
            return False

        # 4) flake.nix must exist in the repository.
        flake_path = os.path.join(ctx.repo_dir, self.FLAKE_FILE)
        return os.path.exists(flake_path)

    def _ensure_old_profile_removed(self, ctx: "RepoContext") -> None:
        """
        Best-effort removal of an existing profile entry.

        This handles the "already provides the following file" conflict by
        removing previous `package-manager` installations before we install
        the new one.

        Any error in `nix profile remove` is intentionally ignored, because
        a missing profile entry is not a fatal condition.
        """
        if shutil.which("nix") is None:
            return

        cmd = f"nix profile remove {self.PROFILE_NAME} || true"
        try:
            # NOTE: no allow_failure here → matches the existing unit tests
            run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)
        except SystemExit:
            # Unit tests explicitly assert this is swallowed
            pass

    def run(self, ctx: "InstallContext") -> None:
        """
        Install Nix flake profile outputs (pkgmgr, default).

        Any failure installing `pkgmgr` is treated as fatal (SystemExit).
        A failure installing `default` is logged but does not abort.
        """
        # Extra guard in case run() is called directly without supports().
        if self._in_nix_shell():
            print(
                "[INFO] IN_NIX_SHELL detected in run(); "
                "skipping Nix flake profile installation."
            )
            return

        # Reuse supports() to keep logic in one place
        if not self.supports(ctx):  # type: ignore[arg-type]
            return

        print("Nix flake detected, attempting to install profile outputs...")

        # Handle the "already installed" case up-front:
        self._ensure_old_profile_removed(ctx)  # type: ignore[arg-type]

        for output in ("pkgmgr", "default"):
            cmd = f"nix profile install {ctx.repo_dir}#{output}"

            try:
                # For 'default' we don't want the process to exit on error
                allow_failure = output == "default"
                run_command(
                    cmd,
                    cwd=ctx.repo_dir,
                    preview=ctx.preview,
                    allow_failure=allow_failure,
                )
                print(f"Nix flake output '{output}' successfully installed.")
            except SystemExit as e:
                print(f"[Error] Failed to install Nix flake output '{output}': {e}")
                if output == "pkgmgr":
                    # Broken main CLI install → fatal
                    raise
                # For 'default' we log and continue
                print(
                    "[Warning] Continuing despite failure to install 'default' "
                    "because 'pkgmgr' is already installed."
                )
                break
