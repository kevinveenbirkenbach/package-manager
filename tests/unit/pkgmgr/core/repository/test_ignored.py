#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from pkgmgr.core.repository.ignored import filter_ignored


class TestFilterIgnored(unittest.TestCase):
    def test_filter_ignored_removes_repos_with_ignore_true(self) -> None:
        repos = [
            {"provider": "github.com", "account": "user", "repository": "a", "ignore": True},
            {"provider": "github.com", "account": "user", "repository": "b", "ignore": False},
            {"provider": "github.com", "account": "user", "repository": "c"},
        ]

        result = filter_ignored(repos)

        identifiers = {(r["provider"], r["account"], r["repository"]) for r in result}
        self.assertNotIn(("github.com", "user", "a"), identifiers)
        self.assertIn(("github.com", "user", "b"), identifiers)
        self.assertIn(("github.com", "user", "c"), identifiers)

    def test_filter_ignored_empty_list_returns_empty_list(self) -> None:
        self.assertEqual(filter_ignored([]), [])


if __name__ == "__main__":
    unittest.main()
