#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer for Debian/Ubuntu system dependencies defined in debian/control.

This installer parses the debian/control file and installs packages from
Build-Depends / Build-Depends-Indep / Depends via apt-get on Debian-based
systems.
"""

import os
import shutil
from typing import List

from pkgmgr.context import RepoContext
from pkgmgr.installers.base import BaseInstaller
from pkgmgr.run_command import run_command


class DebianControlInstaller(BaseInstaller):
    """Install Debian/Ubuntu system packages from debian/control."""

    CONTROL_DIR = "debian"
    CONTROL_FILE = "control"

    def _is_debian_like(self) -> bool:
        return shutil.which("apt-get") is not None

    def _control_path(self, ctx: RepoContext) -> str:
        return os.path.join(ctx.repo_dir, self.CONTROL_DIR, self.CONTROL_FILE)

    def supports(self, ctx: RepoContext) -> bool:
        """
        This installer is supported if:
          - we are on a Debian-like system (apt-get available), and
          - debian/control exists.
        """
        if not self._is_debian_like():
            return False

        return os.path.exists(self._control_path(ctx))

    def _parse_control_dependencies(self, control_path: str) -> List[str]:
        """
        Parse Build-Depends, Build-Depends-Indep and Depends fields
        from debian/control.

        This is a best-effort parser that:
          - joins continuation lines starting with space,
          - splits fields by comma,
          - strips version constraints and alternatives (x | y → x),
          - filters out variable placeholders like ${misc:Depends}.
        """
        if not os.path.exists(control_path):
            return []

        with open(control_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        deps: List[str] = []
        current_key = None
        current_val_lines: List[str] = []

        target_keys = {
            "Build-Depends",
            "Build-Depends-Indep",
            "Depends",
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
                # Take the first alternative: "foo | bar" → "foo"
                if "|" in part:
                    part = part.split("|", 1)[0].strip()
                # Strip version constraints: "pkg (>= 1.0)" → "pkg"
                if " " in part:
                    part = part.split(" ", 1)[0].strip()
                # Skip variable placeholders
                if part.startswith("${") and part.endswith("}"):
                    continue
                if part:
                    deps.append(part)
            current_key = None
            current_val_lines = []

        for line in lines:
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
        Install Debian/Ubuntu system packages via apt-get.
        """
        control_path = self._control_path(ctx)
        packages = self._parse_control_dependencies(control_path)
        if not packages:
            return

        # Update and install in two separate commands for clarity.
        run_command("sudo apt-get update", cwd=ctx.repo_dir, preview=ctx.preview)

        cmd = "sudo apt-get install -y " + " ".join(packages)
        run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)
