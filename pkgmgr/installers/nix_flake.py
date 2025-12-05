#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer for Nix flakes.

If a repository contains flake.nix and the 'nix' command is available, this
installer will try to install profile outputs from the flake.
"""

import os
import shutil

from pkgmgr.context import RepoContext
from pkgmgr.installers.base import BaseInstaller
from pkgmgr.run_command import run_command


class NixFlakeInstaller(BaseInstaller):
    """Install Nix flake profiles for repositories that define flake.nix."""

    FLAKE_FILE = "flake.nix"

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

    def run(self, ctx: RepoContext) -> None:
        """
        Install Nix flake profile outputs (pkgmgr, default).

        Any failure in `nix profile install` is treated as fatal (SystemExit).
        """
        flake_path = os.path.join(ctx.repo_dir, self.FLAKE_FILE)
        if not os.path.exists(flake_path):
            return

        if shutil.which("nix") is None:
            print("Warning: flake.nix found but 'nix' command not available. Skipping flake setup.")
            return

        print("Nix flake detected, attempting to install profile output...")
        for output in ("pkgmgr", "default"):
            cmd = f"nix profile install {ctx.repo_dir}#{output}"
            try:
                run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)
                print(f"Nix flake output '{output}' successfully installed.")
            except SystemExit as e:
                print(f"[Error] Failed to install Nix flake output '{output}': {e}")
                # Hard fail: a broken flake is considered a fatal error.
                raise
