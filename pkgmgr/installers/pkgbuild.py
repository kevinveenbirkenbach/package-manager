#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer for Arch Linux dependencies defined in PKGBUILD files.

This installer extracts depends/makedepends from PKGBUILD and installs them
via pacman on Arch-based systems.
"""

import os
import shutil
import subprocess
from typing import List

from pkgmgr.context import RepoContext
from pkgmgr.installers.base import BaseInstaller
from pkgmgr.run_command import run_command


class PkgbuildInstaller(BaseInstaller):
    """Install Arch dependencies (depends/makedepends) from PKGBUILD."""

    PKGBUILD_NAME = "PKGBUILD"

    def supports(self, ctx: RepoContext) -> bool:
        if shutil.which("pacman") is None:
            return False
        pkgbuild_path = os.path.join(ctx.repo_dir, self.PKGBUILD_NAME)
        return os.path.exists(pkgbuild_path)

    def _extract_pkgbuild_array(self, ctx: RepoContext, var_name: str) -> List[str]:
        """
        Extract a Bash array (depends/makedepends) from PKGBUILD using bash itself.
        Returns a list of package names or an empty list on error.

        Uses a minimal shell environment (no profile/rc) to avoid noise from MOTD
        or interactive shell banners polluting the output.
        """
        pkgbuild_path = os.path.join(ctx.repo_dir, self.PKGBUILD_NAME)
        if not os.path.exists(pkgbuild_path):
            return []

        script = f'source {self.PKGBUILD_NAME} >/dev/null 2>&1; printf "%s\\n" "${{{var_name}[@]}}"'
        try:
            output = subprocess.check_output(
                ["bash", "--noprofile", "--norc", "-c", script],
                cwd=ctx.repo_dir,
                text=True,
            )
        except Exception:
            return []

        packages: List[str] = []
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            packages.append(line)
        return packages

    def run(self, ctx: RepoContext) -> None:
        depends = self._extract_pkgbuild_array(ctx, "depends")
        makedepends = self._extract_pkgbuild_array(ctx, "makedepends")
        all_pkgs = depends + makedepends

        if not all_pkgs:
            return

        cmd = "sudo pacman -S --noconfirm " + " ".join(all_pkgs)
        run_command(cmd, preview=ctx.preview)
