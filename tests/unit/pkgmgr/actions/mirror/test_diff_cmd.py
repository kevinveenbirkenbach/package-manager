#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock, PropertyMock, patch

from pkgmgr.actions.mirror.diff_cmd import diff_mirrors


class TestDiffCmd(unittest.TestCase):
    """
    Unit tests for mirror diff output.
    """

    @patch("pkgmgr.actions.mirror.diff_cmd.build_context")
    def test_diff_mirrors_reports_only_in_config_and_only_in_file(
        self, mock_build_context
    ) -> None:
        ctx = MagicMock()
        ctx.identifier = "id"
        ctx.repo_dir = "/tmp/repo"
        ctx.config_mirrors = {"origin": "a", "cfgonly": "b"}
        ctx.file_mirrors = {"origin": "a", "fileonly": "c"}
        type(ctx).resolved_mirrors = PropertyMock(
            return_value={"origin": "a", "cfgonly": "b", "fileonly": "c"}
        )
        mock_build_context.return_value = ctx

        buf = io.StringIO()
        with redirect_stdout(buf):
            diff_mirrors(
                selected_repos=[{}], repositories_base_dir="/base", all_repos=[]
            )

        out = buf.getvalue()
        self.assertIn("[ONLY IN CONFIG] cfgonly: b", out)
        self.assertIn("[ONLY IN FILE]   fileonly: c", out)

    @patch("pkgmgr.actions.mirror.diff_cmd.build_context")
    def test_diff_mirrors_reports_url_mismatch(self, mock_build_context) -> None:
        ctx = MagicMock()
        ctx.identifier = "id"
        ctx.repo_dir = "/tmp/repo"
        ctx.config_mirrors = {"origin": "a"}
        ctx.file_mirrors = {"origin": "different"}
        type(ctx).resolved_mirrors = PropertyMock(return_value={"origin": "different"})
        mock_build_context.return_value = ctx

        buf = io.StringIO()
        with redirect_stdout(buf):
            diff_mirrors(
                selected_repos=[{}], repositories_base_dir="/base", all_repos=[]
            )

        out = buf.getvalue()
        self.assertIn("[URL MISMATCH]", out)
        self.assertIn("config: a", out)
        self.assertIn("file:   different", out)

    @patch("pkgmgr.actions.mirror.diff_cmd.build_context")
    def test_diff_mirrors_reports_in_sync(self, mock_build_context) -> None:
        ctx = MagicMock()
        ctx.identifier = "id"
        ctx.repo_dir = "/tmp/repo"
        ctx.config_mirrors = {"origin": "a"}
        ctx.file_mirrors = {"origin": "a"}
        type(ctx).resolved_mirrors = PropertyMock(return_value={"origin": "a"})
        mock_build_context.return_value = ctx

        buf = io.StringIO()
        with redirect_stdout(buf):
            diff_mirrors(
                selected_repos=[{}], repositories_base_dir="/base", all_repos=[]
            )

        out = buf.getvalue()
        self.assertIn("[OK] Mirrors in config and MIRRORS file are in sync.", out)


if __name__ == "__main__":
    unittest.main()
