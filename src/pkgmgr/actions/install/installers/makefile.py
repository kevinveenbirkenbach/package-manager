# src/pkgmgr/actions/install/installers/makefile.py
from __future__ import annotations

import os
import re

from pkgmgr.actions.install.context import RepoContext
from pkgmgr.actions.install.installers.base import BaseInstaller
from pkgmgr.core.command.run import run_command


class MakefileInstaller(BaseInstaller):
    layer = "makefile"
    MAKEFILE_NAME = "Makefile"

    def supports(self, ctx: RepoContext) -> bool:
        if os.environ.get("PKGMGR_DISABLE_MAKEFILE_INSTALLER") == "1":
            if not ctx.quiet:
                print(
                    "[INFO] PKGMGR_DISABLE_MAKEFILE_INSTALLER=1 – skipping MakefileInstaller."
                )
            return False

        makefile_path = os.path.join(ctx.repo_dir, self.MAKEFILE_NAME)
        return os.path.exists(makefile_path)

    def _has_install_target(self, makefile_path: str) -> bool:
        try:
            with open(makefile_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            return False

        if re.search(r"^install\s*:", content, flags=re.MULTILINE):
            return True
        if re.search(r"^install-[a-zA-Z0-9_-]*\s*:", content, flags=re.MULTILINE):
            return True
        return False

    def run(self, ctx: RepoContext) -> None:
        makefile_path = os.path.join(ctx.repo_dir, self.MAKEFILE_NAME)
        if not os.path.exists(makefile_path):
            return

        if not self._has_install_target(makefile_path):
            if not ctx.quiet:
                print(f"[pkgmgr] No 'install' target found in {makefile_path}.")
            return

        if not ctx.quiet:
            print(
                f"[pkgmgr] Running make install for {ctx.identifier} (MakefileInstaller)"
            )

        run_command("make install", cwd=ctx.repo_dir, preview=ctx.preview)

        if ctx.force_update and not ctx.quiet:
            print(f"[makefile] repo '{ctx.identifier}' successfully upgraded.")
