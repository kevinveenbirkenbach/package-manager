#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer for Python projects based on pyproject.toml and/or requirements.txt.

Strategy:
  - Determine a pip command in this order:
      1. $PKGMGR_PIP (explicit override, e.g. ~/.venvs/pkgmgr/bin/pip)
      2. sys.executable -m pip (current interpreter)
      3. "pip" from PATH as last resort
  - If pyproject.toml exists: pip install .
  - If requirements.txt exists: pip install -r requirements.txt

All installation failures are treated as fatal errors (SystemExit).
"""

import os
import sys

from pkgmgr.installers.base import BaseInstaller
from pkgmgr.run_command import run_command


class PythonInstaller(BaseInstaller):
    """Install Python projects and dependencies via pip."""

    name = "python"

    def supports(self, ctx) -> bool:
        """
        Return True if this installer should handle the given repository.
        """
        repo_dir = ctx.repo_dir
        return (
            os.path.exists(os.path.join(repo_dir, "pyproject.toml"))
            or os.path.exists(os.path.join(repo_dir, "requirements.txt"))
        )

    def _pip_cmd(self) -> str:
        """
        Resolve the pip command to use.
        """
        explicit = os.environ.get("PKGMGR_PIP", "").strip()
        if explicit:
            return explicit

        if sys.executable:
            return f"{sys.executable} -m pip"

        return "pip"

    def run(self, ctx) -> None:
        """
        Install Python project (pyproject.toml) and/or requirements.txt.

        Any pip failure is propagated as SystemExit.
        """
        pip_cmd = self._pip_cmd()

        pyproject = os.path.join(ctx.repo_dir, "pyproject.toml")
        if os.path.exists(pyproject):
            print(
                f"pyproject.toml found in {ctx.identifier}, "
                f"installing Python project..."
            )
            cmd = f"{pip_cmd} install ."
            run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)

        req_txt = os.path.join(ctx.repo_dir, "requirements.txt")
        if os.path.exists(req_txt):
            print(
                f"requirements.txt found in {ctx.identifier}, "
                f"installing Python dependencies..."
            )
            cmd = f"{pip_cmd} install -r requirements.txt"
            run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)
