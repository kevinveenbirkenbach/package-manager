#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.mirror.context import build_context


class TestMirrorContext(unittest.TestCase):
    """
    Unit tests for building RepoMirrorContext from repo + filesystem.
    """

    @patch("pkgmgr.actions.mirror.context.read_mirrors_file")
    @patch("pkgmgr.actions.mirror.context.load_config_mirrors")
    @patch("pkgmgr.actions.mirror.context.get_repo_dir")
    @patch("pkgmgr.actions.mirror.context.get_repo_identifier")
    def test_build_context_bundles_config_and_file_mirrors(
        self,
        mock_identifier,
        mock_repo_dir,
        mock_load_config,
        mock_read_file,
    ) -> None:
        mock_identifier.return_value = "id"
        mock_repo_dir.return_value = "/tmp/repo"
        mock_load_config.return_value = {"origin": "git@github.com:alice/repo.git"}
        mock_read_file.return_value = {"backup": "ssh://git@backup/alice/repo.git"}

        repo = {"provider": "github.com", "account": "alice", "repository": "repo"}

        ctx = build_context(repo, repositories_base_dir="/base", all_repos=[repo])

        self.assertEqual(ctx.identifier, "id")
        self.assertEqual(ctx.repo_dir, "/tmp/repo")
        self.assertEqual(
            ctx.config_mirrors, {"origin": "git@github.com:alice/repo.git"}
        )
        self.assertEqual(
            ctx.file_mirrors, {"backup": "ssh://git@backup/alice/repo.git"}
        )
        self.assertEqual(
            ctx.resolved_mirrors,
            {
                "origin": "git@github.com:alice/repo.git",
                "backup": "ssh://git@backup/alice/repo.git",
            },
        )


if __name__ == "__main__":
    unittest.main()
