#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer for RPM-based packages defined in *.spec files.

This installer:

  1. Installs build dependencies via dnf/yum builddep (where available)
  2. Uses rpmbuild to build RPMs from the provided .spec file
  3. Installs the resulting RPMs via `rpm -i`

It targets RPM-based systems (Fedora / RHEL / CentOS / Rocky / Alma, etc.).
"""

import glob
import os
import shutil

from typing import List, Optional

from pkgmgr.actions.repository.install.context import RepoContext
from pkgmgr.actions.repository.install.installers.base import BaseInstaller
from pkgmgr.core.command.run import run_command


class RpmSpecInstaller(BaseInstaller):
    """
    Build and install RPM-based packages from *.spec files.

    This installer is responsible for the full build + install of the
    application on RPM-like systems.
    """

    # Logical layer name, used by capability matchers.
    layer = "os-packages"

    def _is_rpm_like(self) -> bool:
        """
        Basic RPM-like detection:

          - rpmbuild must be available
          - at least one of dnf / yum / yum-builddep must be present
        """
        if shutil.which("rpmbuild") is None:
            return False

        has_dnf = shutil.which("dnf") is not None
        has_yum = shutil.which("yum") is not None
        has_yum_builddep = shutil.which("yum-builddep") is not None

        return has_dnf or has_yum or has_yum_builddep

    def _spec_path(self, ctx: RepoContext) -> Optional[str]:
        """Return the first *.spec file in the repository root, if any."""
        pattern = os.path.join(ctx.repo_dir, "*.spec")
        matches = sorted(glob.glob(pattern))
        if not matches:
            return None
        return matches[0]

    def supports(self, ctx: RepoContext) -> bool:
        """
        This installer is supported if:
          - we are on an RPM-based system (rpmbuild + dnf/yum/yum-builddep available), and
          - a *.spec file exists in the repository root.
        """
        if not self._is_rpm_like():
            return False

        return self._spec_path(ctx) is not None

    def _find_built_rpms(self) -> List[str]:
        """
        Find RPMs built by rpmbuild.

        By default, rpmbuild outputs RPMs into:
          ~/rpmbuild/RPMS/*/*.rpm
        """
        home = os.path.expanduser("~")
        pattern = os.path.join(home, "rpmbuild", "RPMS", "**", "*.rpm")
        return sorted(glob.glob(pattern, recursive=True))

    def _install_build_dependencies(self, ctx: RepoContext, spec_path: str) -> None:
        """
        Install build dependencies for the given .spec file.

        Strategy (best-effort):

          1. If dnf is available:
               sudo dnf builddep -y <spec>
          2. Else if yum-builddep is available:
               sudo yum-builddep -y <spec>
          3. Else if yum is available:
               sudo yum-builddep -y <spec>   # Some systems provide it via yum plugin
          4. Otherwise: print a warning and skip automatic builddep install.

        Any failure in builddep installation is treated as fatal (SystemExit),
        consistent with other installer steps.
        """
        spec_basename = os.path.basename(spec_path)

        if shutil.which("dnf") is not None:
            cmd = f"sudo dnf builddep -y {spec_basename}"
        elif shutil.which("yum-builddep") is not None:
            cmd = f"sudo yum-builddep -y {spec_basename}"
        elif shutil.which("yum") is not None:
            # Some distributions ship yum-builddep as a plugin.
            cmd = f"sudo yum-builddep -y {spec_basename}"
        else:
            print(
                "[Warning] No suitable RPM builddep tool (dnf/yum-builddep/yum) found. "
                "Skipping automatic build dependency installation for RPM."
            )
            return

        # Run builddep in the repository directory so relative spec paths work.
        run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)

    def run(self, ctx: RepoContext) -> None:
        """
        Build and install RPM-based packages.

        Steps:
          1. dnf/yum builddep <spec> (automatic build dependency installation)
          2. rpmbuild -ba path/to/spec
          3. sudo rpm -i ~/rpmbuild/RPMS/*/*.rpm
        """
        spec_path = self._spec_path(ctx)
        if not spec_path:
            return

        # 1) Install build dependencies
        self._install_build_dependencies(ctx, spec_path)

        # 2) Build RPMs
        # Use the full spec path, but run in the repo directory.
        spec_basename = os.path.basename(spec_path)
        build_cmd = f"rpmbuild -ba {spec_basename}"
        run_command(build_cmd, cwd=ctx.repo_dir, preview=ctx.preview)

        # 3) Find built RPMs
        rpms = self._find_built_rpms()
        if not rpms:
            print(
                "[Warning] No RPM files found after rpmbuild. "
                "Skipping RPM package installation."
            )
            return

        # 4) Install RPMs
        if shutil.which("rpm") is None:
            print(
                "[Warning] rpm binary not found on PATH. "
                "Cannot install built RPMs."
            )
            return

        install_cmd = "sudo rpm -i " + " ".join(rpms)
        run_command(install_cmd, cwd=ctx.repo_dir, preview=ctx.preview)
