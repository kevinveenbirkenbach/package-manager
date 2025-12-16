from __future__ import annotations

import unittest

from pkgmgr.actions.repository.create.model import RepoParts
from pkgmgr.actions.repository.create.parser import (
    parse_identifier,
    _parse_git_url,
    _strip_git_suffix,
    _split_host_port,
)


class TestRepositoryCreateParsing(unittest.TestCase):
    def test_strip_git_suffix(self) -> None:
        self.assertEqual(_strip_git_suffix("repo.git"), "repo")
        self.assertEqual(_strip_git_suffix("repo"), "repo")

    def test_split_host_port(self) -> None:
        self.assertEqual(_split_host_port("example.com"), ("example.com", None))
        self.assertEqual(_split_host_port("example.com:2222"), ("example.com", "2222"))
        self.assertEqual(_split_host_port("example.com:"), ("example.com", None))

    def test_parse_identifier_plain(self) -> None:
        parts = parse_identifier("github.com/owner/repo")
        self.assertIsInstance(parts, RepoParts)
        self.assertEqual(parts.host, "github.com")
        self.assertEqual(parts.port, None)
        self.assertEqual(parts.owner, "owner")
        self.assertEqual(parts.name, "repo")

    def test_parse_identifier_with_port(self) -> None:
        parts = parse_identifier("gitea.example.com:2222/org/repo")
        self.assertEqual(parts.host, "gitea.example.com")
        self.assertEqual(parts.port, "2222")
        self.assertEqual(parts.owner, "org")
        self.assertEqual(parts.name, "repo")

    def test_parse_git_url_scp_style(self) -> None:
        parts = _parse_git_url("git@github.com:owner/repo.git")
        self.assertEqual(parts.host, "github.com")
        self.assertEqual(parts.port, None)
        self.assertEqual(parts.owner, "owner")
        self.assertEqual(parts.name, "repo")

    def test_parse_git_url_https(self) -> None:
        parts = _parse_git_url("https://github.com/owner/repo.git")
        self.assertEqual(parts.host, "github.com")
        self.assertEqual(parts.port, None)
        self.assertEqual(parts.owner, "owner")
        self.assertEqual(parts.name, "repo")

    def test_parse_git_url_ssh_with_port(self) -> None:
        parts = _parse_git_url("ssh://git@gitea.example.com:2222/org/repo.git")
        self.assertEqual(parts.host, "gitea.example.com")
        self.assertEqual(parts.port, "2222")
        self.assertEqual(parts.owner, "org")
        self.assertEqual(parts.name, "repo")


if __name__ == "__main__":
    unittest.main()
