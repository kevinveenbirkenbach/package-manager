#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer for Python projects based on pyproject.toml.

Strategy:
  - Determine a pip command in this order:
      1. $PKGMGR_PIP (explicit override, e.g. ~/.venvs/pkgmgr/bin/pip)
      2. sys.executable -m pip (current interpreter)
      3. "pip" from PATH as last resort
  - If pyproject.toml exists: pip install .

All installation failures are treated as fatal errors (SystemExit),
except when we explicitly skip the installer:

  - If IN_NIX_SHELL is set, we assume Python is managed by Nix and
    skip this installer entirely.
  - If PKGMGR_DISABLE_PYTHON_INSTALLER=1 is set, the installer is
    globally disabled (useful for CI or debugging).
"""

from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

from pkgmgr.actions.repository.install.installers.base import BaseInstaller
from pkgmgr.core.command.run import run_command

if TYPE_CHECKING:
    from pkgmgr.actions.repository.install.context import RepoContext
    from pkgmgr.actions.repository.install import InstallContext


class PythonInstaller(BaseInstaller):
    """Install Python projects and dependencies via pip."""

    # Logical layer name, used by capability matchers.
    layer = "python"

    def _in_nix_shell(self) -> bool:
        """
        Return True if we appear to be running inside a Nix dev shell.

        Nix sets IN_NIX_SHELL in `nix develop` environments. In that case
        the Python environment is already provided by Nix, so we must not
        attempt an additional pip-based installation.
        """
        return bool(os.environ.get("IN_NIX_SHELL"))

    def supports(self, ctx: "RepoContext") -> bool:
        """
        Return True if this installer should handle the given repository.

        Only pyproject.toml is supported as the single source of truth
        for Python dependencies and packaging metadata.

        The installer is *disabled* when:
          - IN_NIX_SHELL is set (Python managed by Nix dev shell), or
          - PKGMGR_DISABLE_PYTHON_INSTALLER=1 is set.
        """
        # 1) Skip in Nix dev shells – Python is managed by the flake/devShell.
        if self._in_nix_shell():
            print(
                "[INFO] IN_NIX_SHELL detected; skipping PythonInstaller. "
                "Python runtime is provided by the Nix dev shell."
            )
            return False

        # 2) Optional global kill-switch.
        if os.environ.get("PKGMGR_DISABLE_PYTHON_INSTALLER") == "1":
            print(
                "[INFO] PKGMGR_DISABLE_PYTHON_INSTALLER=1 – "
                "PythonInstaller is disabled."
            )
            return False

        repo_dir = ctx.repo_dir
        return os.path.exists(os.path.join(repo_dir, "pyproject.toml"))

    def _pip_cmd(self) -> str:
        """
        Resolve the pip command to use.

        Order:
          1) PKGMGR_PIP (explicit override)
          2) sys.executable -m pip
          3) plain "pip"
        """
        explicit = os.environ.get("PKGMGR_PIP", "").strip()
        if explicit:
            return explicit

        if sys.executable:
            return f"{sys.executable} -m pip"

        return "pip"

    def run(self, ctx: "InstallContext") -> None:
        """
        Install Python project defined via pyproject.toml.

        Any pip failure is propagated as SystemExit.
        """
        # Extra guard in case run() is called directly without supports().
        if self._in_nix_shell():
            print(
                "[INFO] IN_NIX_SHELL detected in PythonInstaller.run(); "
                "skipping pip-based installation."
            )
            return

        if not self.supports(ctx):  # type: ignore[arg-type]
            return

        pip_cmd = self._pip_cmd()

        pyproject = os.path.join(ctx.repo_dir, "pyproject.toml")
        if os.path.exists(pyproject):
            print(
                f"pyproject.toml found in {ctx.identifier}, "
                f"installing Python project..."
            )
            cmd = f"{pip_cmd} install ."
            run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)
