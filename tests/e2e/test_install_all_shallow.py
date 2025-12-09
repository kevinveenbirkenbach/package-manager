"""
Integration test: install all configured repositories using
--clone-mode shallow (HTTPS shallow clone) and --no-verification.

This test is intended to be run inside the Docker container where:
  - network access is available,
  - the config/config.yaml is present,
  - and it is safe to perform real git operations.

It passes if the command completes without raising an exception.
"""

import runpy
import sys
import unittest

from test_integration_install_pkgmgr_shallow import (
    nix_profile_list_debug,
    remove_pkgmgr_from_nix_profile,
    pkgmgr_help_debug,
)


class TestIntegrationInstallAllShallow(unittest.TestCase):
    def _run_pkgmgr_install_all(self) -> None:
        """
        Helper that runs the CLI command via main.py and provides
        extra diagnostics if the command exits with a non-zero code.
        """
        cmd_repr = "pkgmgr install --all --clone-mode shallow --no-verification"
        original_argv = sys.argv
        try:
            sys.argv = [
                "pkgmgr",
                "install",
                "--all",
                "--clone-mode",
                "shallow",
                "--no-verification",
            ]

            try:
                # Execute main.py as if it was called from CLI.
                # This will run the full install pipeline inside the container.
                runpy.run_module("main", run_name="__main__")
            except SystemExit as exc:
                # Convert SystemExit into a more helpful assertion with debug output.
                exit_code = exc.code if isinstance(exc.code, int) else str(exc.code)

                print("\n[TEST] pkgmgr install --all failed with SystemExit")
                print(f"[TEST] Command : {cmd_repr}")
                print(f"[TEST] Exit code: {exit_code}")

                # Additional Nix profile debug on failure
                nix_profile_list_debug("ON FAILURE (AFTER SystemExit)")

                raise AssertionError(
                    f"{cmd_repr!r} failed with exit code {exit_code}. "
                    "Scroll up to see the full pkgmgr/make output inside the container."
                ) from exc

        finally:
            sys.argv = original_argv

    def test_install_all_repositories_shallow(self) -> None:
        """
        Run: pkgmgr install --all --clone-mode shallow --no-verification

        This will perform real installations/clones inside the container.
        The test succeeds if no exception is raised and `pkgmgr --help`
        works in a fresh interactive bash session afterwards.
        """
        # Debug before cleanup
        nix_profile_list_debug("BEFORE CLEANUP")

        # Cleanup: aggressively try to drop any pkgmgr/profile entries
        remove_pkgmgr_from_nix_profile()

        # Debug after cleanup
        nix_profile_list_debug("AFTER CLEANUP")

        # Run the actual install with extended diagnostics
        self._run_pkgmgr_install_all()

        # After successful installation: show `pkgmgr --help`
        # via interactive bash (same as the pkgmgr-only test).
        pkgmgr_help_debug()


if __name__ == "__main__":
    unittest.main()
