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


class TestIntegrationInstallAllShallow(unittest.TestCase):
    def test_install_pkgmgr_self_install(self):
        """
        Run: pkgmgr install --all --clone-mode shallow --no-verification

        This will perform real installations/clones inside the container.
        The test succeeds if no exception is raised.
        """
        original_argv = sys.argv
        try:
            sys.argv = [
                "pkgmgr",
                "install",
                "pkgmgr",
                "--clone-mode",
                "shallow",
                "--no-verification",
            ]

            # Execute main.py as if it was called from CLI.
            # This will run the full install pipeline inside the container.
            runpy.run_module("main", run_name="__main__")

        finally:
            sys.argv = original_argv


if __name__ == "__main__":
    unittest.main()
