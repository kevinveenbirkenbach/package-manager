from __future__ import annotations

import os
import runpy
import sys
import unittest

from test_version_commands import PROJECT_ROOT


class TestIntegrationProxyCommands(unittest.TestCase):
    """
    Integration tests for proxy commands (e.g. git pull) using the new
    selection logic and `--preview` mode so no real changes are made.
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

    def test_git_pull_preview_for_pkgmgr(self) -> None:
        """
        `pkgmgr pull --preview pkgmgr` should go through the proxy layer,
        use get_selected_repos() and only print the underlying git pull
        command without executing it.
        """
        self._run_pkgmgr(
            ["pull", "--preview", "pkgmgr"],
            cwd=PROJECT_ROOT,
        )

    def test_git_pull_preview_with_string_filter(self) -> None:
        """
        `pkgmgr pull --preview --string pkgmgr` exercises the proxy +
        filter-only selection path.
        """
        self._run_pkgmgr(
            ["pull", "--preview", "--string", "pkgmgr"],
            cwd=PROJECT_ROOT,
        )
