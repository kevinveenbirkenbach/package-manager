#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer for RPM-based packages defined in *.spec files.

This installer:

  1. Installs build dependencies via dnf/yum builddep (where available)
  2. Prepares a source tarball in ~/rpmbuild/SOURCES based on the .spec
  3. Uses rpmbuild to build RPMs from the provided .spec file
  4. Installs the resulting RPMs via the system package manager (dnf/yum)
     or rpm as a fallback.

It targets RPM-based systems (Fedora / RHEL / CentOS / Rocky / Alma, etc.).
"""

import glob
import os
import shutil
import tarfile
from typing import List, Optional, Tuple

from pkgmgr.actions.install.context import RepoContext
from pkgmgr.actions.install.installers.base import BaseInstaller
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

    # ------------------------------------------------------------------
    # Helpers for preparing rpmbuild topdir and source tarball
    # ------------------------------------------------------------------
    def _rpmbuild_topdir(self) -> str:
        """
        Return the rpmbuild topdir that rpmbuild will use by default.

        By default this is:  ~/rpmbuild

        In the self-install tests, $HOME is set to /tmp/pkgmgr-self-install,
        so this becomes /tmp/pkgmgr-self-install/rpmbuild which matches the
        paths in the RPM build logs.
        """
        home = os.path.expanduser("~")
        return os.path.join(home, "rpmbuild")

    def _ensure_rpmbuild_tree(self, topdir: str) -> None:
        """
        Ensure the standard rpmbuild directory tree exists:

          <topdir>/
            BUILD/
            BUILDROOT/
            RPMS/
            SOURCES/
            SPECS/
            SRPMS/
        """
        for sub in ("BUILD", "BUILDROOT", "RPMS", "SOURCES", "SPECS", "SRPMS"):
            os.makedirs(os.path.join(topdir, sub), exist_ok=True)

    def _parse_name_version(self, spec_path: str) -> Optional[Tuple[str, str]]:
        """
        Parse Name and Version from the given .spec file.

        Returns (name, version) or None if either cannot be determined.
        """
        name = None
        version = None

        with open(spec_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                # Ignore comments
                if not line or line.startswith("#"):
                    continue

                lower = line.lower()
                if lower.startswith("name:"):
                    # e.g. "Name: package-manager"
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        name = parts[1].strip()
                elif lower.startswith("version:"):
                    # e.g. "Version: 0.7.7"
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        version = parts[1].strip()

                if name and version:
                    break

        if not name or not version:
            print(
                "[Warning] Could not determine Name/Version from spec file "
                f"'{spec_path}'. Skipping RPM source tarball preparation."
            )
            return None

        return name, version

    def _prepare_source_tarball(self, ctx: RepoContext, spec_path: str) -> None:
        """
        Prepare a source tarball in <HOME>/rpmbuild/SOURCES that matches
        the Name/Version in the .spec file.
        """
        parsed = self._parse_name_version(spec_path)
        if parsed is None:
            return

        name, version = parsed
        topdir = self._rpmbuild_topdir()
        self._ensure_rpmbuild_tree(topdir)

        build_dir = os.path.join(topdir, "BUILD")
        sources_dir = os.path.join(topdir, "SOURCES")

        source_root = os.path.join(build_dir, f"{name}-{version}")
        tarball_path = os.path.join(sources_dir, f"{name}-{version}.tar.gz")

        # Clean any previous build directory for this name/version.
        if os.path.exists(source_root):
            shutil.rmtree(source_root)

        # Copy the repository tree into BUILD/<name>-<version>.
        shutil.copytree(ctx.repo_dir, source_root)

        # Create the tarball with the top-level directory <name>-<version>.
        if os.path.exists(tarball_path):
            os.remove(tarball_path)

        with tarfile.open(tarball_path, "w:gz") as tar:
            tar.add(source_root, arcname=f"{name}-{version}")

        print(
            f"[INFO] Prepared RPM source tarball at '{tarball_path}' "
            f"from '{ctx.repo_dir}'."
        )

    # ------------------------------------------------------------------

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
        topdir = self._rpmbuild_topdir()
        pattern = os.path.join(topdir, "RPMS", "**", "*.rpm")
        return sorted(glob.glob(pattern, recursive=True))

    def _install_build_dependencies(self, ctx: RepoContext, spec_path: str) -> None:
        """
        Install build dependencies for the given .spec file.
        """
        spec_basename = os.path.basename(spec_path)

        if shutil.which("dnf") is not None:
            cmd = f"sudo dnf builddep -y {spec_basename}"
        elif shutil.which("yum-builddep") is not None:
            cmd = f"sudo yum-builddep -y {spec_basename}"
        elif shutil.which("yum") is not None:
            cmd = f"sudo yum-builddep -y {spec_basename}"
        else:
            print(
                "[Warning] No suitable RPM builddep tool (dnf/yum-builddep/yum) found. "
                "Skipping automatic build dependency installation for RPM."
            )
            return

        run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)

    def _install_built_rpms(self, ctx: RepoContext, rpms: List[str]) -> None:
        """
        Install or upgrade the built RPMs.

        Strategy:
          - Prefer dnf install -y <rpms> (handles upgrades cleanly)
          - Else yum install -y <rpms>
          - Else fallback to rpm -Uvh <rpms> (upgrade/replace existing)
        """
        if not rpms:
            print(
                "[Warning] No RPM files found after rpmbuild. "
                "Skipping RPM package installation."
            )
            return

        dnf = shutil.which("dnf")
        yum = shutil.which("yum")
        rpm = shutil.which("rpm")

        if dnf is not None:
            install_cmd = "sudo dnf install -y " + " ".join(rpms)
        elif yum is not None:
            install_cmd = "sudo yum install -y " + " ".join(rpms)
        elif rpm is not None:
            # Fallback: use rpm in upgrade mode so an existing older
            # version is replaced instead of causing file conflicts.
            install_cmd = "sudo rpm -Uvh " + " ".join(rpms)
        else:
            print(
                "[Warning] No suitable RPM installer (dnf/yum/rpm) found. "
                "Cannot install built RPMs."
            )
            return

        run_command(install_cmd, cwd=ctx.repo_dir, preview=ctx.preview)

    def run(self, ctx: RepoContext) -> None:
        """
        Build and install RPM-based packages.

        Steps:
          1. Prepare source tarball in ~/rpmbuild/SOURCES matching Name/Version
          2. dnf/yum builddep <spec> (automatic build dependency installation)
          3. rpmbuild -ba path/to/spec
          4. Install built RPMs via dnf/yum (or rpm as fallback)
        """
        spec_path = self._spec_path(ctx)
        if not spec_path:
            return

        # 1) Prepare source tarball so rpmbuild finds Source0 in SOURCES.
        self._prepare_source_tarball(ctx, spec_path)

        # 2) Install build dependencies
        self._install_build_dependencies(ctx, spec_path)

        # 3) Build RPMs
        spec_basename = os.path.basename(spec_path)
        build_cmd = f"rpmbuild -ba {spec_basename}"
        run_command(build_cmd, cwd=ctx.repo_dir, preview=ctx.preview)

        # 4) Find and install built RPMs
        rpms = self._find_built_rpms()
        self._install_built_rpms(ctx, rpms)
