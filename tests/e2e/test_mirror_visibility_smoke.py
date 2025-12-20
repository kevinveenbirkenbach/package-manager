# tests/e2e/test_mirror_visibility_smoke.py
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path


class TestMirrorVisibilityE2ESmoke(unittest.TestCase):
    """
    E2E smoke tests for the new mirror visibility feature.

    We intentionally DO NOT execute provider APIs or require tokens.
    The tests only verify that:
      - CLI exposes the new subcommands / flags via --help
      - Python public API surface is wired and importable

    IMPORTANT:
      - `python -m pkgmgr.cli` is NOT valid unless pkgmgr/cli/__main__.py exists.
      - In this repo, `from pkgmgr.cli import main` is the stable entrypoint.
    """

    @staticmethod
    def _project_root() -> Path:
        # tests/e2e/... -> project root is parents[2]
        return Path(__file__).resolve().parents[2]

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env.setdefault("PYTHONUNBUFFERED", "1")

        return subprocess.run(
            args,
            cwd=str(self._project_root()),
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

    def _run_pkgmgr(self, pkgmgr_args: list[str]) -> subprocess.CompletedProcess[str]:
        """
        Run the pkgmgr CLI in a way that works both:
          - when the console script `pkgmgr` is available on PATH
          - when only source imports are available

        We prefer the console script if present because it's closest to real E2E.
        """
        exe = shutil.which("pkgmgr")
        if exe:
            return self._run([exe, *pkgmgr_args])

        # Fallback to a Python-level entrypoint that exists in your repo:
        # The stacktrace showed: from pkgmgr.cli import main
        # We call it with argv simulation.
        code = r"""
import sys
from pkgmgr.cli import main

sys.argv = ["pkgmgr"] + sys.argv[1:]
main()
"""
        return self._run([sys.executable, "-c", code, *pkgmgr_args])

    def test_cli_help_lists_visibility_and_provision_public(self) -> None:
        # `pkgmgr mirror --help` should mention "visibility"
        p = self._run_pkgmgr(["mirror", "--help"])
        self.assertEqual(
            p.returncode,
            0,
            msg=f"Expected exit code 0, got {p.returncode}\n\nOutput:\n{p.stdout}",
        )
        out_lower = p.stdout.lower()
        self.assertIn("visibility", out_lower)
        self.assertIn("provision", out_lower)

        # `pkgmgr mirror provision --help` should show `--public`
        p = self._run_pkgmgr(["mirror", "provision", "--help"])
        self.assertEqual(
            p.returncode,
            0,
            msg=f"Expected exit code 0, got {p.returncode}\n\nOutput:\n{p.stdout}",
        )
        self.assertIn("--public", p.stdout)

        # `pkgmgr mirror visibility --help` should show choices {private, public}
        p = self._run_pkgmgr(["mirror", "visibility", "--help"])
        self.assertEqual(
            p.returncode,
            0,
            msg=f"Expected exit code 0, got {p.returncode}\n\nOutput:\n{p.stdout}",
        )
        out_lower = p.stdout.lower()
        self.assertIn("private", out_lower)
        self.assertIn("public", out_lower)

    def test_python_api_surface_is_exposed(self) -> None:
        # Ensure public exports exist and setup_mirrors has ensure_visibility in signature.
        code = r"""
import inspect

from pkgmgr.actions import mirror as mirror_actions
from pkgmgr.core import remote_provisioning as rp

assert hasattr(mirror_actions, "set_mirror_visibility"), "set_mirror_visibility missing in pkgmgr.actions.mirror"
assert hasattr(rp, "set_repo_visibility"), "set_repo_visibility missing in pkgmgr.core.remote_provisioning"

sig = inspect.signature(mirror_actions.setup_mirrors)
assert "ensure_visibility" in sig.parameters, "setup_mirrors missing ensure_visibility parameter"

print("OK")
"""
        p = self._run([sys.executable, "-c", code])
        self.assertEqual(
            p.returncode,
            0,
            msg=f"Expected exit code 0, got {p.returncode}\n\nOutput:\n{p.stdout}",
        )
        self.assertIn("OK", p.stdout)


if __name__ == "__main__":
    unittest.main()
