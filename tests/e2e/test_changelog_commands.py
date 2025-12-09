# tests/e2e/test_integration_changelog_commands.py
from __future__ import annotations

import os
import runpy
import sys
import unittest

from test_integration_version_commands import (
    _load_pkgmgr_repo_dir,
    PROJECT_ROOT,
)


class TestIntegrationChangelogCommands(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        """
        Versuche, das pkgmgr-Repository-Verzeichnis aus der Config zu laden.
        Wenn es im aktuellen Test-Container nicht existiert, merken wir uns
        None und überspringen repo-spezifische Tests später sauber.
        """
        try:
            repo_dir = _load_pkgmgr_repo_dir()
        except Exception:
            repo_dir = None

        if repo_dir is not None and not os.path.isdir(repo_dir):
            repo_dir = None

        cls.pkgmgr_repo_dir = repo_dir

    def _run_pkgmgr_changelog(
        self,
        extra_args: list[str] | None = None,
        cwd: str | None = None,
    ) -> None:
        """
        Helper that executes the pkgmgr CLI with the 'changelog' command
        via runpy, similar to the existing version integration tests.
        """
        if extra_args is None:
            extra_args = []

        cmd_repr = "pkgmgr changelog " + " ".join(extra_args)
        original_argv = list(sys.argv)
        original_cwd = os.getcwd()

        try:
            if cwd is not None and os.path.isdir(cwd):
                os.chdir(cwd)

            # Simulate CLI invocation: pkgmgr changelog <args...>
            sys.argv = ["pkgmgr", "changelog"] + list(extra_args)

            try:
                runpy.run_module("pkgmgr.cli", run_name="__main__")
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else str(exc.code)
                if code != 0:
                    print()
                    print(f"[TEST] Command          : {cmd_repr}")
                    print(f"[TEST] Working directory: {os.getcwd()}")
                    print(f"[TEST] Exit code        : {code}")
                    raise AssertionError(
                        f"{cmd_repr!r} failed with exit code {code}. "
                        "Scroll up to inspect the pkgmgr output before failure."
                    ) from exc
        finally:
            os.chdir(original_cwd)
            sys.argv = original_argv

    def test_changelog_default_range_current_repo(self) -> None:
        """
        Run 'pkgmgr changelog' inside the pkgmgr repo, using the default range
        (last two SemVer tags or fallback to full history).

        Wird übersprungen, wenn das pkgmgr-Repo in dieser Umgebung
        nicht lokal vorhanden ist.
        """
        if self.pkgmgr_repo_dir is None:
            self.skipTest(
                "pkgmgr repo directory not available in this environment; "
                "skipping repo-local changelog test."
            )

        self._run_pkgmgr_changelog(extra_args=[], cwd=self.pkgmgr_repo_dir)

    def test_changelog_explicit_range_head_history(self) -> None:
        """
        Run 'pkgmgr changelog HEAD~5..HEAD' inside the pkgmgr repo.
        Selbst wenn HEAD~5 nicht existiert, sollte der Befehl den
        GitError intern behandeln und mit Exit-Code 0 beenden
        (es wird dann eine [ERROR]-Zeile gedruckt).

        Wird übersprungen, wenn das pkgmgr-Repo nicht lokal vorhanden ist.
        """
        if self.pkgmgr_repo_dir is None:
            self.skipTest(
                "pkgmgr repo directory not available in this environment; "
                "skipping repo-local changelog range test."
            )

        self._run_pkgmgr_changelog(
            extra_args=["HEAD~5..HEAD"],
            cwd=self.pkgmgr_repo_dir,
        )

    def test_changelog_all_repositories_default(self) -> None:
        """
        Run 'pkgmgr changelog --all' from the project root to ensure
        that repository selection + changelog pipeline work in the
        multi-repo scenario.

        Dieser Test ist robust, selbst wenn einige Repos aus der Config
        physisch nicht existieren: handle_changelog überspringt sie
        mit einer INFO-Meldung.
        """
        self._run_pkgmgr_changelog(
            extra_args=["--all"],
            cwd=PROJECT_ROOT,
        )


if __name__ == "__main__":
    unittest.main()
