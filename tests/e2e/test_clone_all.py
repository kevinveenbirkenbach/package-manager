"""
Integration test: clone all configured repositories using
--clone-mode https and --no-verification.

This test is intended to be run inside the Docker container where:
  - network access is available,
  - the config/config.yaml is present,
  - and it is safe to perform real git operations.

It passes if the command completes without raising an exception.
"""

import runpy
import sys
import unittest

from test_install_pkgmgr_shallow import (
    nix_profile_list_debug,
    remove_pkgmgr_from_nix_profile,
    pkgmgr_help_debug,
)


class TestIntegrationCloneAllHttps(unittest.TestCase):
    def _run_pkgmgr_clone_all_https(self) -> None:
        """
        Helper that runs the CLI command via main.py and provides
        extra diagnostics if the command exits with a non-zero code.
        """
        cmd_repr = "pkgmgr clone --all --clone-mode https --no-verification"
        original_argv = sys.argv
        try:
            sys.argv = [
                "pkgmgr",
                "clone",
                "--all",
                "--clone-mode",
                "https",
                "--no-verification",
            ]

            try:
                # Execute main.py as if it was called from CLI.
                # This will run the full clone pipeline inside the container.
                runpy.run_module("main", run_name="__main__")
            except SystemExit as exc:
                # Convert SystemExit into a more helpful assertion with debug output.
                exit_code = exc.code if isinstance(exc.code, int) else str(exc.code)

                print("\n[TEST] pkgmgr clone --all failed with SystemExit")
                print(f"[TEST] Command : {cmd_repr}")
                print(f"[TEST] Exit code: {exit_code}")

                # Additional Nix profile debug on failure (may still be useful
                # if the clone step interacts with Nix-based tooling).
                nix_profile_list_debug("ON FAILURE (AFTER SystemExit)")

                raise AssertionError(
                    f"{cmd_repr!r} failed with exit code {exit_code}. "
                    "Scroll up to see the full pkgmgr/make output inside the container."
                ) from exc

        finally:
            sys.argv = original_argv

    def test_clone_all_repositories_https(self) -> None:
        """
        Run: pkgmgr clone --all --clone-mode https --no-verification

        This will perform real git clone operations inside the container.
        The test succeeds if no exception is raised and `pkgmgr --help`
        works in a fresh interactive bash session afterwards.
        """
        # Debug before cleanup (reusing the same helpers as the install test).
        nix_profile_list_debug("BEFORE CLEANUP")

        # Cleanup: aggressively try to drop any pkgmgr/profile entries
        # (harmless for a pure clone test but keeps environments comparable).
        remove_pkgmgr_from_nix_profile()

        # Debug after cleanup
        nix_profile_list_debug("AFTER CLEANUP")

        # Run the actual clone with extended diagnostics
        self._run_pkgmgr_clone_all_https()

        # After successful clone: show `pkgmgr --help`
        # via interactive bash (same helper as in the install test).
        pkgmgr_help_debug()


if __name__ == "__main__":
    unittest.main()
