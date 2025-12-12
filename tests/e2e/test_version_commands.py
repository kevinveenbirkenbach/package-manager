#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
End-to-end tests for the `pkgmgr version` command.

We verify three usage patterns:

1) pkgmgr version
   - Run from inside the package-manager repository
     so that "current repository" resolution works.

2) pkgmgr version pkgmgr
   - Run from inside the package-manager repository
     with an explicit identifier.

3) pkgmgr version --all
   - Run from the project root (or wherever the tests are started),
     ensuring that the --all flag does not depend on the current
     working directory.
"""

from __future__ import annotations

import os
import runpy
import sys
import unittest
from typing import List

from pkgmgr.core.config.load import load_config

# Resolve project root (the repo where main.py lives, e.g. /src)
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config", "config.yaml")


def _load_pkgmgr_repo_dir() -> str:
    """
    Load the merged configuration (defaults + user config) and determine
    the directory of the package-manager repository managed by pkgmgr.

    We keep this lookup deliberately flexible to avoid depending on
    specific provider/account values. We match either

        repository == "package-manager"  OR
        alias == "pkgmgr"

    and then derive the repository directory from either an explicit
    'directory' field or from the base repositories directory plus
    provider/account/repository.
    """
    cfg = load_config(CONFIG_PATH) or {}

    directories = cfg.get("directories", {})
    base_repos_dir = os.path.expanduser(directories.get("repositories", ""))

    candidates: List[dict] = cfg.get("repositories", []) or []
    for repo in candidates:
        repo_name = (repo.get("repository") or "").strip()
        alias = (repo.get("alias") or "").strip()

        if repo_name == "package-manager" or alias == "pkgmgr":
            # Prefer an explicit directory if present.
            repo_dir = repo.get("directory")
            if not repo_dir:
                provider = (repo.get("provider") or "").strip()
                account = (repo.get("account") or "").strip()

                # Best-effort reconstruction of the directory path.
                if provider and account and repo_name:
                    repo_dir = os.path.join(
                        base_repos_dir, provider, account, repo_name
                    )
                elif repo_name:
                    # Fallback: place directly under the base repo dir
                    repo_dir = os.path.join(base_repos_dir, repo_name)
                else:
                    # If we still have nothing usable, skip this entry.
                    continue

            return os.path.expanduser(repo_dir)

    raise RuntimeError(
        "Could not locate a 'package-manager' repository entry in the merged "
        "configuration (no entry with repository='package-manager' or "
        "alias='pkgmgr' found)."
    )


class TestIntegrationVersionCommands(unittest.TestCase):
    """
    E2E tests for the pkgmgr 'version' command.

    Important:
    - We treat any non-zero SystemExit as a test failure and print
      helpful diagnostics (command, working directory, exit code).
    """

    @classmethod
    def setUpClass(cls) -> None:
        # Determine the package-manager repo directory from the merged config
        cls.pkgmgr_repo_dir = _load_pkgmgr_repo_dir()

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _run_pkgmgr_version(self, extra_args, cwd: str | None = None) -> None:
        """
        Run `pkgmgr version` with optional extra arguments and
        an optional working directory override.

        Any non-zero exit code is turned into an AssertionError
        with additional diagnostics.
        """
        if extra_args is None:
            extra_args = []

        cmd_repr = "pkgmgr version " + " ".join(extra_args)
        original_argv = list(sys.argv)
        original_cwd = os.getcwd()

        try:
            if cwd is not None:
                os.chdir(cwd)

            sys.argv = ["pkgmgr", "version"] + extra_args

            try:
                runpy.run_module("pkgmgr", run_name="__main__")
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else str(exc.code)
                if code != 0:
                    print("[TEST] SystemExit caught while running pkgmgr version")
                    print(f"[TEST] Command : {cmd_repr}")
                    print(f"[TEST] Working directory: {os.getcwd()}")
                    print(f"[TEST] Exit code: {code}")
                    raise AssertionError(
                        f"{cmd_repr!r} failed with exit code {code}. "
                        "Scroll up to inspect the output printed before failure."
                    ) from exc
                # exit code 0 is considered success

        finally:
            # Restore environment
            os.chdir(original_cwd)
            sys.argv = original_argv

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_version_current_repo(self) -> None:
        """
        Run: pkgmgr version

        We run this from inside the package-manager repository so that
        "current repository" resolution works and no identifier lookup
        for 'src' (or similar) is performed.
        """
        self._run_pkgmgr_version(extra_args=[], cwd=self.pkgmgr_repo_dir)

    def test_version_specific_identifier(self) -> None:
        """
        Run: pkgmgr version pkgmgr

        Also executed from inside the package-manager repository, but
        with an explicit identifier.
        """
        self._run_pkgmgr_version(extra_args=["pkgmgr"], cwd=self.pkgmgr_repo_dir)

    def test_version_all_repositories(self) -> None:
        """
        Run: pkgmgr version --all

        This does not depend on the current working directory, but we
        run it from PROJECT_ROOT for clarity and to mirror typical usage
        in CI.
        """
        self._run_pkgmgr_version(extra_args=["--all"], cwd=PROJECT_ROOT)


if __name__ == "__main__":
    unittest.main()
