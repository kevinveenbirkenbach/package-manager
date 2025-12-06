#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer for RPM-based system dependencies defined in *.spec files.

This installer parses the first *.spec file it finds in the repository
and installs packages from BuildRequires / Requires via dnf or yum on
RPM-based systems (Fedora / RHEL / CentOS / Rocky / Alma, etc.).
"""

import glob
import os
import shutil
from typing import List, Optional

from pkgmgr.context import RepoContext
from pkgmgr.installers.base import BaseInstaller
from pkgmgr.run_command import run_command


class RpmSpecInstaller(BaseInstaller):
    """Install RPM-based system packages from *.spec files."""

    def _is_rpm_like(self) -> bool:
        return shutil.which("dnf") is not None or shutil.which("yum") is not None

    def _spec_path(self, ctx: RepoContext) -> Optional[str]:
        pattern = os.path.join(ctx.repo_dir, "*.spec")
        matches = glob.glob(pattern)
        if not matches:
            return None
        # Take the first match deterministically (sorted)
        return sorted(matches)[0]

    def supports(self, ctx: RepoContext) -> bool:
        """
        This installer is supported if:
          - we are on an RPM-based system (dnf or yum available), and
          - a *.spec file exists in the repository root.
        """
        if not self._is_rpm_like():
            return False

        return self._spec_path(ctx) is not None

    def _parse_spec_dependencies(self, spec_path: str) -> List[str]:
        """
        Parse BuildRequires and Requires from a .spec file.

        Best-effort parser that:
          - joins continuation lines starting with space or tab,
          - splits fields by comma,
          - takes the first token of each entry as the package name,
          - ignores macros and empty entries.
        """
        if not os.path.exists(spec_path):
            return []

        with open(spec_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        deps: List[str] = []
        current_key = None
        current_val_lines: List[str] = []

        target_keys = {
            "BuildRequires",
            "Requires",
        }

        def flush_current():
            nonlocal current_key, current_val_lines, deps
            if not current_key or not current_val_lines:
                return
            value = " ".join(l.strip() for l in current_val_lines)
            # Split by comma into individual dependency expressions
            for part in value.split(","):
                part = part.strip()
                if not part:
                    continue
                # Take first token as package name: "pkg >= 1.0" → "pkg"
                token = part.split()[0].strip()
                if not token:
                    continue
                # Ignore macros like %{?something}
                if token.startswith("%"):
                    continue
                deps.append(token)
            current_key = None
            current_val_lines = []

        for line in lines:
            stripped = line.lstrip()
            if stripped.startswith("#"):
                # Comment
                continue

            if line.startswith(" ") or line.startswith("\t"):
                # Continuation of previous field
                if current_key in target_keys:
                    current_val_lines.append(line)
                continue

            # New field
            flush_current()

            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()

            if key in target_keys:
                current_key = key
                current_val_lines = [val]

        # Flush last field
        flush_current()

        # De-duplicate while preserving order
        seen = set()
        unique_deps: List[str] = []
        for pkg in deps:
            if pkg not in seen:
                seen.add(pkg)
                unique_deps.append(pkg)

        return unique_deps

    def run(self, ctx: RepoContext) -> None:
        """
        Install RPM-based system packages via dnf or yum.
        """
        spec_path = self._spec_path(ctx)
        if not spec_path:
            return

        packages = self._parse_spec_dependencies(spec_path)
        if not packages:
            return

        pkg_mgr = shutil.which("dnf") or shutil.which("yum")
        if not pkg_mgr:
            print(
                "[Warning] No suitable RPM package manager (dnf/yum) found on PATH. "
                "Skipping RPM dependency installation."
            )
            return

        cmd = f"sudo {pkg_mgr} install -y " + " ".join(packages)
        run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)
