#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer that triggers `make install` if a Makefile is present and
the Makefile actually defines an 'install' target.

This is useful for repositories that expose a standard Makefile-based
installation step.
"""

import os
import re

from pkgmgr.actions.repository.install.context import RepoContext
from pkgmgr.actions.repository.install.installers.base import BaseInstaller
from pkgmgr.core.command.run import run_command


class MakefileInstaller(BaseInstaller):
    """Run `make install` if a Makefile with an 'install' target exists."""

    # Logical layer name, used by capability matchers.
    layer = "makefile"

    MAKEFILE_NAME = "Makefile"

    def supports(self, ctx: RepoContext) -> bool:
        """Return True if a Makefile exists in the repository directory."""
        makefile_path = os.path.join(ctx.repo_dir, self.MAKEFILE_NAME)
        return os.path.exists(makefile_path)

    def _has_install_target(self, makefile_path: str) -> bool:
        """
        Check whether the Makefile defines an 'install' target.

        We treat the presence of a real install target as either:
          - a line starting with 'install:' (optionally preceded by whitespace), or
          - a .PHONY line that lists 'install' as one of the targets.
        """
        try:
            with open(makefile_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            # If we cannot read the Makefile for some reason, assume no target.
            return False

        # install: ...
        if re.search(r"^\s*install\s*:", content, flags=re.MULTILINE):
            return True

        # .PHONY: ... install ...
        if re.search(r"^\s*\.PHONY\s*:\s*.*\binstall\b", content, flags=re.MULTILINE):
            return True

        return False

    def run(self, ctx: RepoContext) -> None:
        """
        Execute `make install` in the repository directory, but only if an
        'install' target is actually defined in the Makefile.

        Any failure in `make install` is treated as a fatal error and will
        propagate as SystemExit from run_command().
        """
        makefile_path = os.path.join(ctx.repo_dir, self.MAKEFILE_NAME)

        if not os.path.exists(makefile_path):
            # Should normally not happen if supports() was checked before,
            # but keep this guard for robustness.
            if not ctx.quiet:
                print(
                    f"[pkgmgr] Makefile '{makefile_path}' not found, "
                    "skipping make install."
                )
            return

        if not self._has_install_target(makefile_path):
            if not ctx.quiet:
                print(
                    "[pkgmgr] Skipping Makefile install: no 'install' target "
                    f"found in {makefile_path}."
                )
            return

        if not ctx.quiet:
            print(
                f"[pkgmgr] Running 'make install' in {ctx.repo_dir} "
                "(install target detected in Makefile)."
            )

        cmd = "make install"
        run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)
