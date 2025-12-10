#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
PythonInstaller — install Python projects defined via pyproject.toml.

Installation rules:

1. pip command resolution:
      a) If PKGMGR_PIP is set → use it exactly as provided.
      b) Else if running inside a virtualenv → use `sys.executable -m pip`.
      c) Else → create/use a per-repository virtualenv under ~/.venvs/<repo>/.

2. Installation target:
      - Always install into the resolved pip environment.
      - Never modify system Python, never rely on --user.
      - Nix-immutable systems (PEP 668) are automatically avoided because we
        never touch system Python.

3. The installer is skipped when:
      - PKGMGR_DISABLE_PYTHON_INSTALLER=1 is set.
      - The repository has no pyproject.toml.

All pip failures are treated as fatal.
"""

from __future__ import annotations

import os
import sys
import subprocess
from typing import TYPE_CHECKING

from pkgmgr.actions.repository.install.installers.base import BaseInstaller
from pkgmgr.core.command.run import run_command

if TYPE_CHECKING:
    from pkgmgr.actions.repository.install.context import RepoContext
    from pkgmgr.actions.repository.install import InstallContext


class PythonInstaller(BaseInstaller):
    """Install Python projects and dependencies via pip using isolated environments."""

    layer = "python"

    # ----------------------------------------------------------------------
    # Installer activation logic
    # ----------------------------------------------------------------------
    def supports(self, ctx: "RepoContext") -> bool:
        """
        Return True if this installer should handle this repository.

        The installer is active only when:
          - A pyproject.toml exists in the repo, and
          - PKGMGR_DISABLE_PYTHON_INSTALLER is not set.
        """
        if os.environ.get("PKGMGR_DISABLE_PYTHON_INSTALLER") == "1":
            print("[INFO] PythonInstaller disabled via PKGMGR_DISABLE_PYTHON_INSTALLER.")
            return False

        return os.path.exists(os.path.join(ctx.repo_dir, "pyproject.toml"))

    # ----------------------------------------------------------------------
    # Virtualenv handling
    # ----------------------------------------------------------------------
    def _in_virtualenv(self) -> bool:
        """Detect whether the current interpreter is inside a venv."""
        if os.environ.get("VIRTUAL_ENV"):
            return True

        base = getattr(sys, "base_prefix", sys.prefix)
        return sys.prefix != base

    def _ensure_repo_venv(self, ctx: "InstallContext") -> str:
        """
        Ensure that ~/.venvs/<identifier>/ exists and contains a minimal venv.

        Returns the venv directory path.
        """
        venv_dir = os.path.expanduser(f"~/.venvs/{ctx.identifier}")
        python = sys.executable

        if not os.path.isdir(venv_dir):
            print(f"[python-installer] Creating virtualenv: {venv_dir}")
            subprocess.check_call([python, "-m", "venv", venv_dir])

        return venv_dir

    # ----------------------------------------------------------------------
    # pip command resolution
    # ----------------------------------------------------------------------
    def _pip_cmd(self, ctx: "InstallContext") -> str:
        """
        Determine which pip command to use.

        Priority:
          1. PKGMGR_PIP override given by user or automation.
          2. Active virtualenv → use sys.executable -m pip.
          3. Per-repository venv → ~/.venvs/<repo>/bin/pip
        """
        explicit = os.environ.get("PKGMGR_PIP", "").strip()
        if explicit:
            return explicit

        if self._in_virtualenv():
            return f"{sys.executable} -m pip"

        venv_dir = self._ensure_repo_venv(ctx)
        pip_path = os.path.join(venv_dir, "bin", "pip")
        return pip_path

    # ----------------------------------------------------------------------
    # Execution
    # ----------------------------------------------------------------------
    def run(self, ctx: "InstallContext") -> None:
        """
        Install the project defined by pyproject.toml.

        Uses the resolved pip environment. Installation is isolated and never
        touches system Python.
        """
        if not self.supports(ctx):  # type: ignore[arg-type]
            return

        pyproject = os.path.join(ctx.repo_dir, "pyproject.toml")
        if not os.path.exists(pyproject):
            return

        print(f"[python-installer] Installing Python project for {ctx.identifier}...")

        pip_cmd = self._pip_cmd(ctx)

        # Final install command: ALWAYS isolated, never system-wide.
        install_cmd = f"{pip_cmd} install ."

        run_command(install_cmd, cwd=ctx.repo_dir, preview=ctx.preview)

        print(f"[python-installer] Installation finished for {ctx.identifier}.")
