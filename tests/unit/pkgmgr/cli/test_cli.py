#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the pkgmgr CLI (version command).

These tests focus on the 'version' subcommand and its interaction with:
- git tags (SemVer),
- pyproject.toml version,
- and the mismatch warning logic.

Important:
- Uses only the Python standard library unittest framework.
- Does not use pytest.
- Does not rely on a real git repository or real config files.
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from typing import Any, Dict, List
from unittest import mock

from pkgmgr import cli


def _fake_config() -> Dict[str, Any]:
    """
    Provide a minimal configuration dict sufficient for cli.main()
    to start without touching real config files.
    """
    return {
        "directories": {
            "repositories": "/tmp/pkgmgr-repos",
            "binaries": "/tmp/pkgmgr-bin",
            "workspaces": "/tmp/pkgmgr-workspaces",
        },
        # The actual list of repositories is not used directly by the tests,
        # because we mock the selection logic. It must exist, though.
        "repositories": [],
    }


class TestCliVersion(unittest.TestCase):
    """
    Tests for the 'pkgmgr version' command.

    Each test:
    - Runs in a temporary working directory.
    - Uses a fake configuration via load_config().
    - Uses the same selection logic as the new CLI:
      * dispatch_command() calls _select_repo_for_current_directory()
        when there is no explicit selection.
    """

    def setUp(self) -> None:
        # Create a temporary directory and switch into it
        self._tmp_dir = tempfile.TemporaryDirectory()
        self._old_cwd = os.getcwd()
        os.chdir(self._tmp_dir.name)

        # Define a fake repo pointing to our temp dir
        self._fake_repo = {
            "provider": "github.com",
            "account": "test",
            "repository": "pkgmgr-test",
            "directory": self._tmp_dir.name,
        }

        # Patch load_config so cli.main() does not read real config files
        self._patch_load_config = mock.patch(
            "pkgmgr.cli.load_config", return_value=_fake_config()
        )
        self.mock_load_config = self._patch_load_config.start()

        # Patch the "current directory" selection used by dispatch_command().
        # This matches the new behaviour: without explicit identifiers,
        # version uses _select_repo_for_current_directory(ctx).
        self._patch_select_repo_for_current_directory = mock.patch(
            "pkgmgr.cli.dispatch._select_repo_for_current_directory",
            return_value=[self._fake_repo],
        )
        self.mock_select_repo_for_current_directory = (
            self._patch_select_repo_for_current_directory.start()
        )

        # Keep a reference to the original sys.argv, so we can restore it
        self._old_argv = list(sys.argv)

    def tearDown(self) -> None:
        # Restore sys.argv
        sys.argv = self._old_argv

        # Stop all patches
        self._patch_select_repo_for_current_directory.stop()
        self._patch_load_config.stop()

        # Restore working directory
        os.chdir(self._old_cwd)

        # Cleanup temp directory
        self._tmp_dir.cleanup()

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------

    def _write_pyproject(self, version: str) -> str:
        """
        Write a minimal PEP 621-style pyproject.toml into the temp directory.
        """
        content = textwrap.dedent(
            f"""
            [project]
            name = "pkgmgr-test"
            version = "{version}"
            """
        ).strip() + "\n"

        path = os.path.join(self._tmp_dir.name, "pyproject.toml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def _run_cli_version_and_capture(
        self,
        extra_args: List[str] | None = None,
    ) -> str:
        """
        Run 'pkgmgr version [extra_args]' via cli.main() and return captured stdout.
        """
        if extra_args is None:
            extra_args = []

        sys.argv = ["pkgmgr", "version"] + list(extra_args)
        buf = io.StringIO()
        with redirect_stdout(buf):
            try:
                cli.main()
            except SystemExit as exc:
                # Re-raise as AssertionError to make failures easier to read
                raise AssertionError(
                    f"'pkgmgr version' exited with code {exc.code}"
                ) from exc
        return buf.getvalue()

    # ------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------

    def test_version_matches_tag(self) -> None:
        """
        If the latest SemVer tag matches the pyproject.toml version,
        the CLI should:
        - show both values
        - NOT emit a mismatch warning.
        """
        # Arrange: pyproject.toml with version 1.2.3
        self._write_pyproject("1.2.3")

        # Arrange: mock git tags used by handle_version
        with mock.patch(
            "pkgmgr.cli.commands.version.get_tags",
            return_value=["v1.2.0", "v1.2.3", "v1.0.0"],
        ):
            # Act
            stdout = self._run_cli_version_and_capture()

        # Basic header
        self.assertIn("pkgmgr version info", stdout)
        self.assertIn("Repository:", stdout)

        # Git SemVer tag line
        self.assertIn("Git (latest SemVer tag):", stdout)
        self.assertIn("v1.2.3", stdout)
        self.assertIn("(parsed: 1.2.3)", stdout)

        # pyproject line
        self.assertIn("pyproject.toml:", stdout)
        self.assertIn("1.2.3", stdout)

        # No warning expected if versions are equal
        self.assertNotIn("[WARN]", stdout)

    def test_version_mismatch_warns(self) -> None:
        """
        If the latest SemVer tag differs from the pyproject.toml version,
        the CLI should emit a mismatch warning.
        """
        # Arrange: pyproject.toml says 1.2.4
        self._write_pyproject("1.2.4")

        # Arrange: mock git tags (latest is 1.2.3)
        with mock.patch(
            "pkgmgr.cli.commands.version.get_tags",
            return_value=["v1.2.3"],
        ):
            stdout = self._run_cli_version_and_capture()

        # Git line
        self.assertIn("Git (latest SemVer tag):", stdout)
        self.assertIn("v1.2.3", stdout)

        # pyproject line
        self.assertIn("pyproject.toml:", stdout)
        self.assertIn("1.2.4", stdout)

        # Mismatch warning must be printed
        self.assertIn("[WARN]", stdout)
        self.assertIn("Version mismatch", stdout)

    def test_version_no_tags(self) -> None:
        """
        If no tags exist at all, the CLI should handle this gracefully,
        show "<none found>" for tags and still display the pyproject version.
        No mismatch warning should be emitted because there is no tag.
        """
        # Arrange: pyproject.toml exists
        self._write_pyproject("0.0.1")

        # Arrange: no tags returned
        with mock.patch(
            "pkgmgr.cli.commands.version.get_tags",
            return_value=[],
        ):
            stdout = self._run_cli_version_and_capture()

        # Indicates that no SemVer tag was found
        self.assertIn("Git (latest SemVer tag): <none found>", stdout)

        # pyproject version is still shown
        self.assertIn("pyproject.toml:", stdout)
        self.assertIn("0.0.1", stdout)

        # No mismatch warning expected
        self.assertNotIn("Version mismatch", stdout)
        self.assertNotIn("[WARN]", stdout)


if __name__ == "__main__":
    unittest.main()
