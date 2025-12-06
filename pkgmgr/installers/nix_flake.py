#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer for Nix flakes.

If a repository contains flake.nix and the 'nix' command is available, this
installer will try to install profile outputs from the flake.

Behavior:
  - If flake.nix is present and `nix` exists on PATH:
      * First remove any existing `package-manager` profile entry (best-effort).
      * Then install the flake outputs (pkgmgr, default) via `nix profile install`.
  - Any failure in `nix profile install` is treated as fatal (SystemExit).
"""

import os
import shutil

from pkgmgr.context import RepoContext
from pkgmgr.installers.base import BaseInstaller
from pkgmgr.run_command import run_command


class NixFlakeInstaller(BaseInstaller):
    """Install Nix flake profiles for repositories that define flake.nix."""

    FLAKE_FILE = "flake.nix"
    PROFILE_NAME = "package-manager"

    def supports(self, ctx: RepoContext) -> bool:
        """
        Only support repositories that:
          - Have a flake.nix
          - And have the `nix` command available.
        """
        if shutil.which("nix") is None:
            return False
        flake_path = os.path.join(ctx.repo_dir, self.FLAKE_FILE)
        return os.path.exists(flake_path)

    def _ensure_old_profile_removed(self, ctx: RepoContext) -> None:
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

        # We do NOT use run_command here, because we explicitly want to ignore
        # the failure of `nix profile remove` (e.g. entry not present).
        # Using `|| true` makes this idempotent.
        cmd = f"nix profile remove {self.PROFILE_NAME} || true"
        # This will still respect preview mode inside run_command.
        try:
            run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)
        except SystemExit:
            # Ignore any error here: if the profile entry does not exist,
            # that's fine and not a fatal condition.
            pass

    def run(self, ctx: RepoContext) -> None:
        """
        Install Nix flake profile outputs (pkgmgr, default).

        Any failure in `nix profile install` is treated as fatal (SystemExit).
        The "already installed / file conflict" situation is avoided by
        removing the existing profile entry beforehand.
        """
        flake_path = os.path.join(ctx.repo_dir, self.FLAKE_FILE)
        if not os.path.exists(flake_path):
            return

        if shutil.which("nix") is None:
            print("Warning: flake.nix found but 'nix' command not available. Skipping flake setup.")
            return

        print("Nix flake detected, attempting to install profile outputs...")

        # Handle the "already installed" case up-front:
        self._ensure_old_profile_removed(ctx)

        for output in ("pkgmgr", "default"):
            cmd = f"nix profile install {ctx.repo_dir}#{output}"
            try:
                run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)
                print(f"Nix flake output '{output}' successfully installed.")
            except SystemExit as e:
                print(f"[Error] Failed to install Nix flake output '{output}': {e}")
                # Hard fail: a broken flake is considered a fatal error.
                raise
