#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
E2E test to inspect the Nix environment and build the pkgmgr flake
in *every* distro container.

Commands executed inside the container (for all distros):

    nix --version
    nix show-config | grep sandbox
    id
    nix build .#pkgmgr -L

No docker is called from here – the outer test harness
(scripts/test/test-e2e.sh) is responsible for starting the container.
"""

from __future__ import annotations

import os
import subprocess
import unittest


# Resolve project root (the repo where flake.nix lives, e.g. /src)
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


def _run_cmd(cmd: list[str]) -> subprocess.CompletedProcess:
    """
    Run a command in a subprocess, capture stdout/stderr and print them.

    Does NOT raise by itself – the caller checks returncode.
    """
    print("\n[TEST] Running command:", " ".join(cmd))
    proc = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
    )
    print("[STDOUT]\n", proc.stdout)
    print("[STDERR]\n", proc.stderr)
    print("[RETURN CODE]", proc.returncode)
    return proc


class TestNixBuildPkgmgrAllDistros(unittest.TestCase):
    """
    E2E test that runs the same Nix diagnostics + flake build
    in all distro containers.
    """

    def test_nix_env_and_build_pkgmgr(self) -> None:
        # Ensure we are in the project root (where flake.nix resides)
        original_cwd = os.getcwd()
        try:
            os.chdir(PROJECT_ROOT)

            # --- Nix version ---
            _run_cmd(["nix", "--version"])

            # --- Nix sandbox setting ---
            _run_cmd(["sh", "-c", "nix show-config | grep sandbox || true"])

            # --- Current user ---
            _run_cmd(["id"])

            # --- nix build .#pkgmgr -L ---
            proc = _run_cmd([
                "nix",
                "--option", "sandbox", "false",
                "build", ".#pkgmgr",
                "-L",
            ])
            
            if proc.returncode != 0:
                raise AssertionError(
                    "nix build .#pkgmgr -L failed inside the test container.\n"
                    f"Exit code: {proc.returncode}\n"
                    "See STDOUT/STDERR above for Nix diagnostics."
                )

        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
