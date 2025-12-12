from __future__ import annotations

import os
import runpy
import sys
import unittest

from test_version_commands import PROJECT_ROOT


class TestIntegrationListCommands(unittest.TestCase):
    """
    Integration tests for `pkgmgr list` with the new selection and
    description behaviour.
    """

    def _run_pkgmgr(self, args: list[str], cwd: str | None = None) -> None:
        cmd_repr = "pkgmgr " + " ".join(args)
        original_argv = list(sys.argv)
        original_cwd = os.getcwd()

        try:
            if cwd is not None:
                os.chdir(cwd)

            # Simulate: pkgmgr <args...>
            sys.argv = ["pkgmgr"] + args

            try:
                runpy.run_module("pkgmgr", run_name="__main__")
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else str(exc.code)
                if code != 0:
                    print()
                    print(f"[TEST] Command          : {cmd_repr}")
                    print(f"[TEST] Working directory: {os.getcwd()}")
                    print(f"[TEST] Exit code        : {code}")
                    raise AssertionError(
                        f"{cmd_repr!r} failed with exit code {code}. "
                        "Scroll up to inspect the output printed before failure."
                    ) from exc
        finally:
            os.chdir(original_cwd)
            sys.argv = original_argv

    def test_list_all_repositories(self) -> None:
        """
        `pkgmgr list --all` should successfully print the summary table.
        """
        self._run_pkgmgr(["list", "--all"], cwd=PROJECT_ROOT)

    def test_list_all_with_description(self) -> None:
        """
        `pkgmgr list --all --description` should print the table plus the
        detailed section for each repository.
        """
        self._run_pkgmgr(["list", "--all", "--description"], cwd=PROJECT_ROOT)

    def test_list_with_string_filter(self) -> None:
        """
        `pkgmgr list --string pkgmgr` exercises the new string-based
        selection logic on top of the defaults + user config.
        """
        self._run_pkgmgr(["list", "--string", "pkgmgr"], cwd=PROJECT_ROOT)
