#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.mirror.git_remote import (
    build_default_ssh_url,
    determine_primary_remote_url,
    current_origin_url,
    has_origin_remote,
)
from pkgmgr.actions.mirror.types import MirrorMap, Repository


class TestMirrorGitRemote(unittest.TestCase):
    """
    Unit tests for SSH URL and primary remote selection logic.
    """

    def test_build_default_ssh_url_without_port(self) -> None:
        repo: Repository = {
            "provider": "github.com",
            "account": "kevinveenbirkenbach",
            "repository": "package-manager",
        }

        url = build_default_ssh_url(repo)
        self.assertEqual(url, "git@github.com:kevinveenbirkenbach/package-manager.git")

    def test_build_default_ssh_url_with_port(self) -> None:
        repo: Repository = {
            "provider": "code.cymais.cloud",
            "account": "kevinveenbirkenbach",
            "repository": "pkgmgr",
            "port": 2201,
        }

        url = build_default_ssh_url(repo)
        self.assertEqual(url, "ssh://git@code.cymais.cloud:2201/kevinveenbirkenbach/pkgmgr.git")

    def test_build_default_ssh_url_missing_fields_returns_none(self) -> None:
        repo: Repository = {
            "provider": "github.com",
            "account": "kevinveenbirkenbach",
        }

        url = build_default_ssh_url(repo)
        self.assertIsNone(url)

    def test_determine_primary_remote_url_prefers_origin_in_resolved_mirrors(self) -> None:
        repo: Repository = {
            "provider": "github.com",
            "account": "kevinveenbirkenbach",
            "repository": "package-manager",
        }
        mirrors: MirrorMap = {
            "origin": "git@github.com:kevinveenbirkenbach/package-manager.git",
            "backup": "ssh://git@git.veen.world:2201/kevinveenbirkenbach/pkgmgr.git",
        }

        url = determine_primary_remote_url(repo, mirrors)
        self.assertEqual(url, "git@github.com:kevinveenbirkenbach/package-manager.git")

    def test_determine_primary_remote_url_uses_any_mirror_if_no_origin(self) -> None:
        repo: Repository = {
            "provider": "github.com",
            "account": "kevinveenbirkenbach",
            "repository": "package-manager",
        }
        mirrors: MirrorMap = {
            "backup": "ssh://git@git.veen.world:2201/kevinveenbirkenbach/pkgmgr.git",
            "mirror2": "ssh://git@code.cymais.cloud:2201/kevinveenbirkenbach/pkgmgr.git",
        }

        url = determine_primary_remote_url(repo, mirrors)
        self.assertEqual(url, "ssh://git@git.veen.world:2201/kevinveenbirkenbach/pkgmgr.git")

    def test_determine_primary_remote_url_falls_back_to_default_ssh(self) -> None:
        repo: Repository = {
            "provider": "github.com",
            "account": "kevinveenbirkenbach",
            "repository": "package-manager",
        }
        mirrors: MirrorMap = {}

        url = determine_primary_remote_url(repo, mirrors)
        self.assertEqual(url, "git@github.com:kevinveenbirkenbach/package-manager.git")

    @patch("pkgmgr.actions.mirror.git_remote.run_git")
    def test_current_origin_url_returns_value(self, mock_run_git) -> None:
        mock_run_git.return_value = "git@github.com:alice/repo.git\n"
        self.assertEqual(current_origin_url("/tmp/repo"), "git@github.com:alice/repo.git")
        mock_run_git.assert_called_once_with(["remote", "get-url", "origin"], cwd="/tmp/repo")

    @patch("pkgmgr.actions.mirror.git_remote.run_git")
    def test_current_origin_url_returns_none_on_git_error(self, mock_run_git) -> None:
        from pkgmgr.core.git import GitError

        mock_run_git.side_effect = GitError("fail")
        self.assertIsNone(current_origin_url("/tmp/repo"))

    @patch("pkgmgr.actions.mirror.git_remote.run_git")
    def test_has_origin_remote_true(self, mock_run_git) -> None:
        mock_run_git.return_value = "origin\nupstream\n"
        self.assertTrue(has_origin_remote("/tmp/repo"))
        mock_run_git.assert_called_once_with(["remote"], cwd="/tmp/repo")

    @patch("pkgmgr.actions.mirror.git_remote.run_git")
    def test_has_origin_remote_false_on_missing_remote(self, mock_run_git) -> None:
        mock_run_git.return_value = "upstream\n"
        self.assertFalse(has_origin_remote("/tmp/repo"))

    @patch("pkgmgr.actions.mirror.git_remote.run_git")
    def test_has_origin_remote_false_on_git_error(self, mock_run_git) -> None:
        from pkgmgr.core.git import GitError

        mock_run_git.side_effect = GitError("fail")
        self.assertFalse(has_origin_remote("/tmp/repo"))


if __name__ == "__main__":
    unittest.main()
