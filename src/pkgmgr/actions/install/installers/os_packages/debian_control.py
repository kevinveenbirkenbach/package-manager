#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer for Debian/Ubuntu packages defined via debian/control.

This installer:

  1. Installs build dependencies via `apt-get build-dep ./`
  2. Uses dpkg-buildpackage to build .deb packages from debian/*
  3. Installs the resulting .deb files via `dpkg -i`

It is intended for Debian-based systems where dpkg-buildpackage and
apt/dpkg tooling are available.
"""

import glob
import os
import shutil
from typing import List, Optional

from pkgmgr.actions.install.context import RepoContext
from pkgmgr.actions.install.installers.base import BaseInstaller
from pkgmgr.core.command.run import run_command


class DebianControlInstaller(BaseInstaller):
    """
    Build and install a Debian/Ubuntu package from debian/control.

    This installer is responsible for the full build + install of the
    application on Debian-like systems.
    """

    # Logical layer name, used by capability matchers.
    layer = "os-packages"

    CONTROL_DIR = "debian"
    CONTROL_FILE = "control"

    def _is_debian_like(self) -> bool:
        """Return True if this looks like a Debian-based system."""
        return shutil.which("dpkg-buildpackage") is not None

    def _control_path(self, ctx: RepoContext) -> str:
        return os.path.join(ctx.repo_dir, self.CONTROL_DIR, self.CONTROL_FILE)

    def supports(self, ctx: RepoContext) -> bool:
        """
        This installer is supported if:
          - we are on a Debian-like system (dpkg-buildpackage available), and
          - debian/control exists.
        """
        if not self._is_debian_like():
            return False

        return os.path.exists(self._control_path(ctx))

    def _find_built_debs(self, repo_dir: str) -> List[str]:
        """
        Find .deb files built by dpkg-buildpackage.

        By default, dpkg-buildpackage creates .deb files in the parent
        directory of the source tree.
        """
        parent = os.path.dirname(repo_dir)
        pattern = os.path.join(parent, "*.deb")
        return sorted(glob.glob(pattern))

    def _privileged_prefix(self) -> Optional[str]:
        """
        Determine how to run privileged commands:

          - If 'sudo' is available, return 'sudo '.
          - If we are running as root (e.g. inside CI/container), return ''.
          - Otherwise, return None, meaning we cannot safely elevate.

        Callers are responsible for handling the None case (usually by
        warning and skipping automatic installation).
        """
        sudo_path = shutil.which("sudo")

        is_root = False
        try:
            is_root = os.geteuid() == 0
        except AttributeError:  # pragma: no cover - non-POSIX platforms
            # On non-POSIX systems, fall back to assuming "not root".
            is_root = False

        if sudo_path is not None:
            return "sudo "
        if is_root:
            return ""
        return None

    def _install_build_dependencies(self, ctx: RepoContext) -> None:
        """
        Install build dependencies using `apt-get build-dep ./`.

        This is a best-effort implementation that assumes:
          - deb-src entries are configured in /etc/apt/sources.list*,
          - apt-get is available on PATH.

        Any failure is treated as fatal (SystemExit), just like other
        installer steps.
        """
        if shutil.which("apt-get") is None:
            print(
                "[Warning] apt-get not found on PATH. "
                "Skipping automatic build-dep installation for Debian."
            )
            return

        prefix = self._privileged_prefix()
        if prefix is None:
            print(
                "[Warning] Neither 'sudo' is available nor running as root. "
                "Skipping automatic build-dep installation for Debian. "
                "Please install build dependencies from debian/control manually."
            )
            return

        # Update package lists first for reliable build-dep resolution.
        run_command(
            f"{prefix}apt-get update",
            cwd=ctx.repo_dir,
            preview=ctx.preview,
        )

        # Install build dependencies based on debian/control in the current tree.
        # `apt-get build-dep ./` uses the source in the current directory.
        builddep_cmd = f"{prefix}apt-get build-dep -y ./"
        run_command(builddep_cmd, cwd=ctx.repo_dir, preview=ctx.preview)

    def run(self, ctx: RepoContext) -> None:
        """
        Build and install Debian/Ubuntu packages from debian/*.

        Steps:
          1. apt-get build-dep ./ (automatic build dependency installation)
          2. dpkg-buildpackage -b -us -uc
          3. sudo dpkg -i ../*.deb   (or plain dpkg -i when running as root)
        """
        control_path = self._control_path(ctx)
        if not os.path.exists(control_path):
            return

        # 1) Install build dependencies
        self._install_build_dependencies(ctx)

        # 2) Build the package
        build_cmd = "dpkg-buildpackage -b -us -uc"
        run_command(build_cmd, cwd=ctx.repo_dir, preview=ctx.preview)

        # 3) Locate built .deb files
        debs = self._find_built_debs(ctx.repo_dir)
        if not debs:
            print(
                "[Warning] No .deb files found after dpkg-buildpackage. "
                "Skipping Debian package installation."
            )
            return

        prefix = self._privileged_prefix()
        if prefix is None:
            print(
                "[Warning] Neither 'sudo' is available nor running as root. "
                "Skipping automatic .deb installation. "
                "You can manually install the following files with dpkg -i:\n  "
                + "\n  ".join(debs)
            )
            return

        # 4) Install .deb files
        install_cmd = prefix + "dpkg -i " + " ".join(os.path.basename(d) for d in debs)
        parent = os.path.dirname(ctx.repo_dir)
        run_command(install_cmd, cwd=parent, preview=ctx.preview)
