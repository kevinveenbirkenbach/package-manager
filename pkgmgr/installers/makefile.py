#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer that triggers `make install` if a Makefile is present.

This is useful for repositories that expose a standard Makefile-based
installation step.
"""

import os

from pkgmgr.context import RepoContext
from pkgmgr.installers.base import BaseInstaller
from pkgmgr.run_command import run_command


class MakefileInstaller(BaseInstaller):
    """Run `make install` if a Makefile exists in the repository."""

    MAKEFILE_NAME = "Makefile"

    def supports(self, ctx: RepoContext) -> bool:
        makefile_path = os.path.join(ctx.repo_dir, self.MAKEFILE_NAME)
        return os.path.exists(makefile_path)

    def run(self, ctx: RepoContext) -> None:
        """
        Execute `make install` in the repository directory.

        Any failure in `make install` is treated as a fatal error and will
        propagate as SystemExit from run_command().
        """
        cmd = "make install"
        run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)
