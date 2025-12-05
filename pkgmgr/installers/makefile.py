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
        cmd = "make install"
        try:
            run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)
        except SystemExit as exc:
            print(f"[Warning] Failed to run '{cmd}' for {ctx.identifier}: {exc}")
