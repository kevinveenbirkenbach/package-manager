#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, PropertyMock, patch

from pkgmgr.actions.mirror.remote_provision import ensure_remote_repository


class TestRemoteProvision(unittest.TestCase):
    """
    Unit tests for remote provisioning wrapper logic (action layer).
    """

    @patch("pkgmgr.actions.mirror.remote_provision.ensure_remote_repo")
    @patch("pkgmgr.actions.mirror.remote_provision.determine_primary_remote_url")
    @patch("pkgmgr.actions.mirror.remote_provision.build_context")
    def test_ensure_remote_repository_builds_spec_from_url_and_calls_core(
        self,
        mock_build_context,
        mock_determine_primary,
        mock_ensure_remote_repo,
    ) -> None:
        ctx = MagicMock()
        type(ctx).resolved_mirrors = PropertyMock(
            return_value={"origin": "ssh://git@git.veen.world:2201/alice/repo.git"}
        )
        ctx.identifier = "repo-id"
        mock_build_context.return_value = ctx

        mock_determine_primary.return_value = (
            "ssh://git@git.veen.world:2201/alice/repo.git"
        )

        result = MagicMock()
        result.status = "created"
        result.message = "Repository created (user)."
        result.url = "https://git.veen.world/alice/repo"
        mock_ensure_remote_repo.return_value = result

        repo = {
            "provider": "gitea",
            "account": "SHOULD_NOT_BE_USED_ANYMORE",
            "repository": "SHOULD_NOT_BE_USED_ANYMORE",
            "private": True,
            "description": "desc",
        }

        ensure_remote_repository(
            repo=repo,
            repositories_base_dir="/base",
            all_repos=[],
            preview=False,
        )

        self.assertTrue(mock_ensure_remote_repo.called)
        called_spec = mock_ensure_remote_repo.call_args[0][0]
        self.assertEqual(called_spec.host, "git.veen.world")
        self.assertEqual(called_spec.owner, "alice")
        self.assertEqual(called_spec.name, "repo")

    @patch("pkgmgr.actions.mirror.remote_provision.ensure_remote_repo")
    @patch("pkgmgr.actions.mirror.remote_provision.determine_primary_remote_url")
    @patch("pkgmgr.actions.mirror.remote_provision.build_context")
    def test_ensure_remote_repository_skips_when_no_primary_url(
        self,
        mock_build_context,
        mock_determine_primary,
        mock_ensure_remote_repo,
    ) -> None:
        ctx = MagicMock()
        type(ctx).resolved_mirrors = PropertyMock(return_value={})
        ctx.identifier = "repo-id"
        mock_build_context.return_value = ctx
        mock_determine_primary.return_value = None

        ensure_remote_repository(
            repo={"provider": "gitea"},
            repositories_base_dir="/base",
            all_repos=[],
            preview=False,
        )

        mock_ensure_remote_repo.assert_not_called()

    @patch("pkgmgr.actions.mirror.remote_provision.ensure_remote_repo")
    @patch("pkgmgr.actions.mirror.remote_provision.determine_primary_remote_url")
    @patch("pkgmgr.actions.mirror.remote_provision.build_context")
    def test_ensure_remote_repository_skips_when_url_not_parseable(
        self,
        mock_build_context,
        mock_determine_primary,
        mock_ensure_remote_repo,
    ) -> None:
        ctx = MagicMock()
        type(ctx).resolved_mirrors = PropertyMock(
            return_value={"origin": "ssh://git@host:2201/not-enough-parts"}
        )
        ctx.identifier = "repo-id"
        mock_build_context.return_value = ctx
        mock_determine_primary.return_value = "ssh://git@host:2201/not-enough-parts"

        ensure_remote_repository(
            repo={"provider": "gitea"},
            repositories_base_dir="/base",
            all_repos=[],
            preview=False,
        )

        mock_ensure_remote_repo.assert_not_called()


if __name__ == "__main__":
    unittest.main()
