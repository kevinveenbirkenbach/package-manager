from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace

from pkgmgr.cli.commands.publish import handle_publish


def _run(cmd: list[str], cwd: str) -> None:
    subprocess.run(
        cmd,
        cwd=cwd,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


class TestIntegrationPublish(unittest.TestCase):
    def setUp(self) -> None:
        if shutil.which("git") is None:
            self.skipTest("git is required for this integration test")

        self.tmp = tempfile.TemporaryDirectory()
        self.repo_dir = self.tmp.name

        # Initialize git repository
        _run(["git", "init"], cwd=self.repo_dir)
        _run(["git", "config", "user.email", "ci@example.invalid"], cwd=self.repo_dir)
        _run(["git", "config", "user.name", "CI"], cwd=self.repo_dir)

        with open(os.path.join(self.repo_dir, "README.md"), "w", encoding="utf-8") as f:
            f.write("test\n")

        _run(["git", "add", "README.md"], cwd=self.repo_dir)
        _run(["git", "commit", "-m", "init"], cwd=self.repo_dir)
        _run(["git", "tag", "-a", "v1.2.3", "-m", "v1.2.3"], cwd=self.repo_dir)

        # Create MIRRORS file with PyPI target
        with open(os.path.join(self.repo_dir, "MIRRORS"), "w", encoding="utf-8") as f:
            f.write("https://pypi.org/project/pkgmgr/\n")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_publish_preview_end_to_end(self) -> None:
        ctx = SimpleNamespace(
            repositories_base_dir=self.repo_dir,
            all_repositories=[
                {
                    "name": "pkgmgr",
                    "directory": self.repo_dir,
                }
            ],
        )

        selected = [
            {
                "name": "pkgmgr",
                "directory": self.repo_dir,
            }
        ]

        args = SimpleNamespace(
            preview=True,
            non_interactive=False,
        )

        buf = io.StringIO()
        with redirect_stdout(buf):
            handle_publish(args=args, ctx=ctx, selected=selected)

        out = buf.getvalue()

        self.assertIn("[pkgmgr] Publishing repository", out)
        self.assertIn("[INFO] Publishing pkgmgr for tag v1.2.3", out)
        self.assertIn("[PREVIEW] Would build and upload to PyPI.", out)

        # Preview must not create dist/
        self.assertFalse(os.path.isdir(os.path.join(self.repo_dir, "dist")))

    def test_publish_skips_without_pypi_mirror(self) -> None:
        with open(os.path.join(self.repo_dir, "MIRRORS"), "w", encoding="utf-8") as f:
            f.write("git@github.com:example/example.git\n")

        ctx = SimpleNamespace(
            repositories_base_dir=self.repo_dir,
            all_repositories=[
                {
                    "name": "pkgmgr",
                    "directory": self.repo_dir,
                }
            ],
        )

        selected = [
            {
                "name": "pkgmgr",
                "directory": self.repo_dir,
            }
        ]

        args = SimpleNamespace(
            preview=True,
            non_interactive=False,
        )

        buf = io.StringIO()
        with redirect_stdout(buf):
            handle_publish(args=args, ctx=ctx, selected=selected)

        out = buf.getvalue()
        self.assertIn("[INFO] No PyPI mirror found. Skipping publish.", out)
