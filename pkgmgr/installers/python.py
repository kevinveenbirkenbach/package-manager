import os
import sys

from .base import BaseInstaller
from pkgmgr.run_command import run_command


class PythonInstaller(BaseInstaller):
    """
    Install Python projects based on pyproject.toml and/or requirements.txt.

    Strategy:
      - Determine a pip command in this order:
          1. $PKGMGR_PIP (explicit override, e.g. ~/.venvs/pkgmgr/bin/pip)
          2. sys.executable -m pip (current interpreter)
          3. "pip" from PATH as last resort
      - If pyproject.toml exists: pip install .
      - If requirements.txt exists: pip install -r requirements.txt
    """

    name = "python"

    def supports(self, ctx) -> bool:
        """
        Return True if this installer should handle the given repository.

        ctx must provide:
          - repo_dir: filesystem path to the repository
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
        # 1) Explicit override via environment variable
        explicit = os.environ.get("PKGMGR_PIP", "").strip()
        if explicit:
            return explicit

        # 2) Current Python interpreter (works well in Nix/dev shells)
        if sys.executable:
            return f"{sys.executable} -m pip"

        # 3) Fallback to plain pip
        return "pip"

    def run(self, ctx) -> None:
        """
        ctx must provide:
          - repo_dir: path to repository
          - identifier: human readable name
          - preview: bool
        """
        pip_cmd = self._pip_cmd()

        pyproject = os.path.join(ctx.repo_dir, "pyproject.toml")
        if os.path.exists(pyproject):
            print(
                f"pyproject.toml found in {ctx.identifier}, "
                f"installing Python project..."
            )
            cmd = f"{pip_cmd} install ."
            try:
                run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)
            except SystemExit as exc:
                print(
                    f"[Warning] Failed to install Python project in {ctx.identifier}: {exc}"
                )

        req_txt = os.path.join(ctx.repo_dir, "requirements.txt")
        if os.path.exists(req_txt):
            print(
                f"requirements.txt found in {ctx.identifier}, "
                f"installing Python dependencies..."
            )
            cmd = f"{pip_cmd} install -r requirements.txt"
            try:
                run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)
            except SystemExit as exc:
                print(
                    f"[Warning] Failed to install Python dependencies in {ctx.identifier}: {exc}"
                )


