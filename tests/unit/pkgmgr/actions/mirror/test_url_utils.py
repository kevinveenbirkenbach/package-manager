#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest

from pkgmgr.actions.mirror.url_utils import hostport_from_git_url, normalize_provider_host, parse_repo_from_git_url


class TestUrlUtils(unittest.TestCase):
    """
    Unit tests for URL parsing helpers used in mirror setup/provisioning.
    """

    def test_hostport_from_git_url_ssh_url_with_port(self) -> None:
        host, port = hostport_from_git_url("ssh://git@code.example.org:2201/alice/repo.git")
        self.assertEqual(host, "code.example.org")
        self.assertEqual(port, "2201")

    def test_hostport_from_git_url_https_url_no_port(self) -> None:
        host, port = hostport_from_git_url("https://github.com/alice/repo.git")
        self.assertEqual(host, "github.com")
        self.assertIsNone(port)

    def test_hostport_from_git_url_scp_like(self) -> None:
        host, port = hostport_from_git_url("git@github.com:alice/repo.git")
        self.assertEqual(host, "github.com")
        self.assertIsNone(port)

    def test_hostport_from_git_url_empty(self) -> None:
        host, port = hostport_from_git_url("")
        self.assertEqual(host, "")
        self.assertIsNone(port)

    def test_normalize_provider_host_strips_port_and_lowercases(self) -> None:
        self.assertEqual(normalize_provider_host("GIT.VEEN.WORLD:2201"), "git.veen.world")

    def test_normalize_provider_host_ipv6_brackets(self) -> None:
        self.assertEqual(normalize_provider_host("[::1]"), "::1")

    def test_normalize_provider_host_empty(self) -> None:
        self.assertEqual(normalize_provider_host(""), "")

    def test_parse_repo_from_git_url_ssh_url(self) -> None:
        host, owner, name = parse_repo_from_git_url("ssh://git@code.example.org:2201/alice/repo.git")
        self.assertEqual(host, "code.example.org")
        self.assertEqual(owner, "alice")
        self.assertEqual(name, "repo")

    def test_parse_repo_from_git_url_https_url(self) -> None:
        host, owner, name = parse_repo_from_git_url("https://github.com/alice/repo.git")
        self.assertEqual(host, "github.com")
        self.assertEqual(owner, "alice")
        self.assertEqual(name, "repo")

    def test_parse_repo_from_git_url_scp_like(self) -> None:
        host, owner, name = parse_repo_from_git_url("git@github.com:alice/repo.git")
        self.assertEqual(host, "github.com")
        self.assertEqual(owner, "alice")
        self.assertEqual(name, "repo")

    def test_parse_repo_from_git_url_best_effort_host_owner_repo(self) -> None:
        host, owner, name = parse_repo_from_git_url("git.veen.world/alice/repo.git")
        self.assertEqual(host, "git.veen.world")
        self.assertEqual(owner, "alice")
        self.assertEqual(name, "repo")

    def test_parse_repo_from_git_url_missing_owner_repo_returns_none(self) -> None:
        host, owner, name = parse_repo_from_git_url("https://github.com/")
        self.assertEqual(host, "github.com")
        self.assertIsNone(owner)
        self.assertIsNone(name)


if __name__ == "__main__":
    unittest.main()
