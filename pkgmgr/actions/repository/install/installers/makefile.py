from __future__ import annotations

import os
import re

from pkgmgr.actions.repository.install.context import RepoContext
from pkgmgr.actions.repository.install.installers.base import BaseInstaller
from pkgmgr.core.command.run import run_command


class MakefileInstaller(BaseInstaller):
    """
    Generic installer that runs `make install` if a Makefile with an
    install target is present.

    Safety rules:
      - If PKGMGR_DISABLE_MAKEFILE_INSTALLER=1 is set, this installer
        is globally disabled.
      - The higher-level InstallationPipeline ensures that Makefile
        installation does not run if a stronger CLI layer already owns
        the command (e.g. Nix or OS packages).
    """

    layer = "makefile"
    MAKEFILE_NAME = "Makefile"

    def supports(self, ctx: RepoContext) -> bool:
        """
        Return True if this repository has a Makefile and the installer
        is not globally disabled.
        """
        # Optional global kill switch.
        if os.environ.get("PKGMGR_DISABLE_MAKEFILE_INSTALLER") == "1":
            if not ctx.quiet:
                print(
                    "[INFO] MakefileInstaller is disabled via "
                    "PKGMGR_DISABLE_MAKEFILE_INSTALLER."
                )
            return False

        makefile_path = os.path.join(ctx.repo_dir, self.MAKEFILE_NAME)
        return os.path.exists(makefile_path)

    def _has_install_target(self, makefile_path: str) -> bool:
        """
        Heuristically check whether the Makefile defines an install target.

        We look for:

          - a plain 'install:' target, or
          - any 'install-*:' style target.
        """
        try:
            with open(makefile_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            return False

        # Simple heuristics: look for "install:" or targets starting with "install-"
        if re.search(r"^install\s*:", content, flags=re.MULTILINE):
            return True

        if re.search(r"^install-[a-zA-Z0-9_-]*\s*:", content, flags=re.MULTILINE):
            return True

        return False

    def run(self, ctx: RepoContext) -> None:
        """
        Execute `make install` in the repository directory if an install
        target exists.
        """
        makefile_path = os.path.join(ctx.repo_dir, self.MAKEFILE_NAME)

        if not os.path.exists(makefile_path):
            if not ctx.quiet:
                print(
                    f"[pkgmgr] Makefile '{makefile_path}' not found, "
                    "skipping MakefileInstaller."
                )
            return

        if not self._has_install_target(makefile_path):
            if not ctx.quiet:
                print(
                    f"[pkgmgr] No 'install' target found in {makefile_path}."
                )
            return

        if not ctx.quiet:
            print(
                f"[pkgmgr] Running 'make install' in {ctx.repo_dir} "
                f"(MakefileInstaller)"
            )

        cmd = "make install"
        run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)
