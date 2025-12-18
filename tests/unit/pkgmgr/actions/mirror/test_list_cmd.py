#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import MagicMock, PropertyMock, patch

from pkgmgr.actions.mirror.list_cmd import list_mirrors


class TestListCmd(unittest.TestCase):
    """
    Unit tests for mirror list output.
    """

    @patch("pkgmgr.actions.mirror.list_cmd.build_context")
    def test_list_mirrors_all_sources_prints_sections(self, mock_build_context) -> None:
        ctx = MagicMock()
        ctx.identifier = "id"
        ctx.repo_dir = "/tmp/repo"
        ctx.config_mirrors = {"origin": "a"}
        ctx.file_mirrors = {"backup": "b"}
        type(ctx).resolved_mirrors = PropertyMock(
            return_value={"origin": "a", "backup": "b"}
        )
        mock_build_context.return_value = ctx

        buf = io.StringIO()
        with redirect_stdout(buf):
            list_mirrors(
                selected_repos=[{}],
                repositories_base_dir="/base",
                all_repos=[],
                source="all",
            )

        out = buf.getvalue()
        self.assertIn("[config mirrors]", out)
        self.assertIn("[MIRRORS file]", out)
        self.assertIn("[resolved mirrors]", out)
        self.assertIn("origin: a", out)
        self.assertIn("backup: b", out)

    @patch("pkgmgr.actions.mirror.list_cmd.build_context")
    def test_list_mirrors_config_only(self, mock_build_context) -> None:
        ctx = MagicMock()
        ctx.identifier = "id"
        ctx.repo_dir = "/tmp/repo"
        ctx.config_mirrors = {"origin": "a"}
        ctx.file_mirrors = {"backup": "b"}
        type(ctx).resolved_mirrors = PropertyMock(
            return_value={"origin": "a", "backup": "b"}
        )
        mock_build_context.return_value = ctx

        buf = io.StringIO()
        with redirect_stdout(buf):
            list_mirrors(
                selected_repos=[{}],
                repositories_base_dir="/base",
                all_repos=[],
                source="config",
            )

        out = buf.getvalue()
        self.assertIn("[config mirrors]", out)
        self.assertIn("origin: a", out)
        self.assertNotIn("[MIRRORS file]", out)
        self.assertNotIn("[resolved mirrors]", out)


if __name__ == "__main__":
    unittest.main()
