#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, PropertyMock, patch

from pkgmgr.actions.mirror.setup_cmd import setup_mirrors


class TestMirrorSetupCmd(unittest.TestCase):
    """
    Unit tests for mirror setup orchestration (local + remote).
    """

    @patch("pkgmgr.actions.mirror.setup_cmd.ensure_origin_remote")
    @patch("pkgmgr.actions.mirror.setup_cmd.build_context")
    def test_setup_mirrors_local_calls_ensure_origin_remote(
        self,
        mock_build_context,
        mock_ensure_origin,
    ) -> None:
        ctx = MagicMock()
        ctx.identifier = "repo-id"
        ctx.repo_dir = "/tmp/repo"
        ctx.config_mirrors = {}
        ctx.file_mirrors = {}
        type(ctx).resolved_mirrors = PropertyMock(return_value={})
        mock_build_context.return_value = ctx

        repo = {"provider": "github.com", "account": "alice", "repository": "repo"}

        setup_mirrors(
            selected_repos=[repo],
            repositories_base_dir="/base",
            all_repos=[repo],
            preview=True,
            local=True,
            remote=False,
            ensure_remote=False,
        )

        mock_ensure_origin.assert_called_once()
        args, kwargs = mock_ensure_origin.call_args
        self.assertEqual(args[0], repo)
        self.assertEqual(kwargs.get("preview"), True)

    @patch("pkgmgr.actions.mirror.setup_cmd.ensure_remote_repository")
    @patch("pkgmgr.actions.mirror.setup_cmd.probe_mirror")
    @patch("pkgmgr.actions.mirror.setup_cmd.build_context")
    def test_setup_mirrors_remote_provisions_when_enabled(
        self,
        mock_build_context,
        mock_probe,
        mock_ensure_remote_repository,
    ) -> None:
        ctx = MagicMock()
        ctx.identifier = "repo-id"
        ctx.repo_dir = "/tmp/repo"
        ctx.config_mirrors = {"origin": "git@github.com:alice/repo.git"}
        ctx.file_mirrors = {}
        type(ctx).resolved_mirrors = PropertyMock(return_value={"origin": "git@github.com:alice/repo.git"})
        mock_build_context.return_value = ctx

        mock_probe.return_value = (True, "")

        repo = {"provider": "github.com", "account": "alice", "repository": "repo"}

        setup_mirrors(
            selected_repos=[repo],
            repositories_base_dir="/base",
            all_repos=[repo],
            preview=False,
            local=False,
            remote=True,
            ensure_remote=True,
        )

        mock_ensure_remote_repository.assert_called_once()
        mock_probe.assert_called_once()

    @patch("pkgmgr.actions.mirror.setup_cmd.ensure_remote_repository")
    @patch("pkgmgr.actions.mirror.setup_cmd.probe_mirror")
    @patch("pkgmgr.actions.mirror.setup_cmd.build_context")
    def test_setup_mirrors_remote_probes_all_resolved_mirrors(
        self,
        mock_build_context,
        mock_probe,
        mock_ensure_remote_repository,
    ) -> None:
        ctx = MagicMock()
        ctx.identifier = "repo-id"
        ctx.repo_dir = "/tmp/repo"
        ctx.config_mirrors = {}
        ctx.file_mirrors = {}
        type(ctx).resolved_mirrors = PropertyMock(
            return_value={
                "mirror": "git@github.com:alice/repo.git",
                "backup": "ssh://git@git.veen.world:2201/alice/repo.git",
            }
        )
        mock_build_context.return_value = ctx

        mock_probe.return_value = (True, "")

        repo = {"provider": "github.com", "account": "alice", "repository": "repo"}

        setup_mirrors(
            selected_repos=[repo],
            repositories_base_dir="/base",
            all_repos=[repo],
            preview=False,
            local=False,
            remote=True,
            ensure_remote=False,
        )

        mock_ensure_remote_repository.assert_not_called()
        self.assertEqual(mock_probe.call_count, 2)


if __name__ == "__main__":
    unittest.main()
