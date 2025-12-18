# src/pkgmgr/actions/install/installers/python.py
from __future__ import annotations

import os
import sys

from pkgmgr.actions.install.installers.base import BaseInstaller
from pkgmgr.actions.install.context import RepoContext
from pkgmgr.core.command.run import run_command


class PythonInstaller(BaseInstaller):
    layer = "python"

    def supports(self, ctx: RepoContext) -> bool:
        if os.environ.get("PKGMGR_DISABLE_PYTHON_INSTALLER") == "1":
            print(
                "[INFO] PythonInstaller disabled via PKGMGR_DISABLE_PYTHON_INSTALLER."
            )
            return False

        return os.path.exists(os.path.join(ctx.repo_dir, "pyproject.toml"))

    def _in_virtualenv(self) -> bool:
        if os.environ.get("VIRTUAL_ENV"):
            return True
        base = getattr(sys, "base_prefix", sys.prefix)
        return sys.prefix != base

    def _ensure_repo_venv(self, ctx: RepoContext) -> str:
        venv_dir = os.path.expanduser(f"~/.venvs/{ctx.identifier}")
        python = sys.executable

        if not os.path.exists(venv_dir):
            run_command(f"{python} -m venv {venv_dir}", preview=ctx.preview)

        return venv_dir

    def _pip_cmd(self, ctx: RepoContext) -> str:
        explicit = os.environ.get("PKGMGR_PIP", "").strip()
        if explicit:
            return explicit

        if self._in_virtualenv():
            return f"{sys.executable} -m pip"

        venv_dir = self._ensure_repo_venv(ctx)
        return os.path.join(venv_dir, "bin", "pip")

    def run(self, ctx: RepoContext) -> None:
        if not self.supports(ctx):
            return

        print(f"[python-installer] Installing Python project for {ctx.identifier}...")

        pip_cmd = self._pip_cmd(ctx)
        run_command(f"{pip_cmd} install .", cwd=ctx.repo_dir, preview=ctx.preview)

        if ctx.force_update:
            # test-visible marker
            print(f"[python-installer] repo '{ctx.identifier}' successfully upgraded.")

        print(f"[python-installer] Installation finished for {ctx.identifier}.")
