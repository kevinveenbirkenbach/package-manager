from __future__ import annotations

import os
import shutil
import subprocess
import unittest


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _run_help(cmd: list[str], label: str) -> str:
    print(f"\n[TEST] Running ({label}): {' '.join(cmd)}")
    proc = subprocess.run(
        cmd,
        cwd=PROJECT_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env=os.environ.copy(),
    )
    print(proc.stdout.rstrip())

    # For --help we expect success (0). Anything else is an error.
    if proc.returncode != 0:
        raise AssertionError(
            f"[TEST] Help command failed ({label}).\n"
            f"Command: {' '.join(cmd)}\n"
            f"Exit code: {proc.returncode}\n"
            f"--- output ---\n{proc.stdout}\n"
        )

    return proc.stdout


class TestPublishHelpE2E(unittest.TestCase):
    def test_pkgmgr_publish_help(self) -> None:
        out = _run_help(["pkgmgr", "publish", "--help"], "pkgmgr publish --help")
        self.assertIn("usage:", out)
        self.assertIn("publish", out)

    def test_pkgmgr_help_mentions_publish(self) -> None:
        out = _run_help(["pkgmgr", "--help"], "pkgmgr --help")
        self.assertIn("publish", out)

    def test_nix_run_pkgmgr_publish_help(self) -> None:
        if shutil.which("nix") is None:
            self.skipTest("nix is not available in this environment")

        out = _run_help(
            ["nix", "run", ".#pkgmgr", "--", "publish", "--help"],
            "nix run .#pkgmgr -- publish --help",
        )
        self.assertIn("usage:", out)
        self.assertIn("publish", out)

    def test_nix_run_pkgmgr_help_mentions_publish(self) -> None:
        if shutil.which("nix") is None:
            self.skipTest("nix is not available in this environment")

        out = _run_help(
            ["nix", "run", ".#pkgmgr", "--", "--help"],
            "nix run .#pkgmgr -- --help",
        )
        self.assertIn("publish", out)


if __name__ == "__main__":
    unittest.main()
