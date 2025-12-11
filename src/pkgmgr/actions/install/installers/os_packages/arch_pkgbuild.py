# pkgmgr/installers/os_packages/arch_pkgbuild.py

import os
import shutil

from pkgmgr.actions.install.context import RepoContext
from pkgmgr.actions.install.installers.base import BaseInstaller
from pkgmgr.core.command.run import run_command


class ArchPkgbuildInstaller(BaseInstaller):
    """
    Build and install an Arch package from PKGBUILD via makepkg.

    This installer is responsible for the full build + install of the
    application on Arch-based systems. System dependencies are resolved
    by makepkg itself (--syncdeps).

    Note: makepkg must not be run as root, so this installer refuses
    to run when the current user is UID 0.
    """

    # Logical layer name, used by capability matchers.
    layer = "os-packages"

    PKGBUILD_NAME = "PKGBUILD"

    def supports(self, ctx: RepoContext) -> bool:
        """
        This installer is supported if:
          - pacman and makepkg are available,
          - a PKGBUILD file exists in the repository root,
          - the current user is NOT root (makepkg forbids root).
        """
        # Do not run makepkg as root – it is explicitly forbidden.
        try:
            if hasattr(os, "geteuid") and os.geteuid() == 0:
                return False
        except Exception:
            # On non-POSIX platforms just ignore this check.
            pass

        if shutil.which("pacman") is None or shutil.which("makepkg") is None:
            return False

        pkgbuild_path = os.path.join(ctx.repo_dir, self.PKGBUILD_NAME)
        return os.path.exists(pkgbuild_path)

    def run(self, ctx: RepoContext) -> None:
        """
        Build and install the package using makepkg.

        This uses:
          makepkg --syncdeps --cleanbuild --install --noconfirm

        Any failure is treated as fatal (SystemExit).
        """
        cmd = "makepkg --syncdeps --cleanbuild --install --noconfirm"
        run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)
