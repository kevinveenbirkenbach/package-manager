"""
Integration test: update all configured repositories using
--clone-mode https and --no-verification.

This test is intended to be run inside the Docker container where:
  - network access is available,
  - the config/config.yaml is present,
  - and it is safe to perform real git operations.

It passes if BOTH commands complete successfully (in separate tests):
  1) pkgmgr update --all --clone-mode https --no-verification
  2) nix run .#pkgmgr -- update --all --clone-mode https --no-verification
"""

import os
import subprocess
import unittest

from test_install_pkgmgr_shallow import (
    nix_profile_list_debug,
    remove_pkgmgr_from_nix_profile,
    pkgmgr_help_debug,
)


class TestIntegrationUpdateAllHttps(unittest.TestCase):
    def _run_cmd(self, cmd: list[str], label: str) -> None:
        """
        Run a real CLI command and raise a helpful assertion on failure.
        """
        cmd_repr = " ".join(cmd)
        env = os.environ.copy()

        try:
            print(f"\n[TEST] Running ({label}): {cmd_repr}")
            subprocess.run(
                cmd,
                check=True,
                cwd=os.getcwd(),
                env=env,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            print(f"\n[TEST] Command failed ({label})")
            print(f"[TEST] Command : {cmd_repr}")
            print(f"[TEST] Exit code: {exc.returncode}")

            nix_profile_list_debug(f"ON FAILURE ({label})")

            raise AssertionError(
                f"({label}) {cmd_repr!r} failed with exit code {exc.returncode}. "
                "Scroll up to see the full pkgmgr/nix output inside the container."
            ) from exc

    def _common_setup(self) -> None:
        # Debug before cleanup
        nix_profile_list_debug("BEFORE CLEANUP")

        # Cleanup: aggressively try to drop any pkgmgr/profile entries
        # (keeps the environment comparable to other integration tests).
        remove_pkgmgr_from_nix_profile()

        # Debug after cleanup
        nix_profile_list_debug("AFTER CLEANUP")

    def test_update_all_repositories_https_pkgmgr(self) -> None:
        """
        Run: pkgmgr update --all --clone-mode https --no-verification
        """
        self._common_setup()

        args = ["update", "--all", "--clone-mode", "https", "--no-verification"]
        self._run_cmd(["pkgmgr", *args], label="pkgmgr")

        # After successful update: show `pkgmgr --help` via interactive bash
        pkgmgr_help_debug()

    def test_update_all_repositories_https_nix_pkgmgr(self) -> None:
        """
        Run: nix run .#pkgmgr -- update --all --clone-mode https --no-verification
        """
        self._common_setup()

        args = ["update", "--all", "--clone-mode", "https", "--no-verification"]
        self._run_cmd(["nix", "run", ".#pkgmgr", "--", *args], label="nix run .#pkgmgr")

        # After successful update: show `pkgmgr --help` via interactive bash
        pkgmgr_help_debug()


if __name__ == "__main__":
    unittest.main()
