import unittest
from unittest.mock import patch

from pkgmgr.core.repository.resolve import resolve_repos


class TestResolveRepos(unittest.TestCase):
    def setUp(self) -> None:
        # Two repos share the same repository name "common" to test uniqueness logic
        self.repos = [
            {
                "provider": "github.com",
                "account": "alice",
                "repository": "demo",
                "alias": "d",
            },
            {
                "provider": "github.com",
                "account": "bob",
                "repository": "common",
                "alias": "c1",
            },
            {
                "provider": "gitlab.com",
                "account": "carol",
                "repository": "common",
                "alias": "c2",
            },
        ]

    def test_matches_full_identifier(self):
        result = resolve_repos(["github.com/alice/demo"], self.repos)
        self.assertEqual(result, [self.repos[0]])

    def test_matches_alias(self):
        result = resolve_repos(["d"], self.repos)
        self.assertEqual(result, [self.repos[0]])

    def test_matches_unique_repository_name_only_if_unique(self):
        # "demo" is unique -> match
        result = resolve_repos(["demo"], self.repos)
        self.assertEqual(result, [self.repos[0]])

        # "common" is NOT unique -> should not match anything
        result2 = resolve_repos(["common"], self.repos)
        self.assertEqual(result2, [])

    def test_multiple_identifiers_accumulate_matches_in_order(self):
        result = resolve_repos(["d", "github.com/bob/common"], self.repos)
        self.assertEqual(result, [self.repos[0], self.repos[1]])

    def test_unknown_identifier_prints_message(self):
        with patch("builtins.print") as mock_print:
            result = resolve_repos(["does-not-exist"], self.repos)

        self.assertEqual(result, [])
        mock_print.assert_called_with(
            "Identifier 'does-not-exist' did not match any repository in config."
        )

    def test_duplicate_identifiers_return_duplicates(self):
        # Current behavior: duplicates are not de-duplicated
        result = resolve_repos(["d", "d"], self.repos)
        self.assertEqual(result, [self.repos[0], self.repos[0]])

    def test_empty_identifiers_returns_empty_list(self):
        result = resolve_repos([], self.repos)
        self.assertEqual(result, [])

    def test_empty_repo_list_returns_empty_list_and_prints(self):
        with patch("builtins.print") as mock_print:
            result = resolve_repos(["github.com/alice/demo"], [])

        self.assertEqual(result, [])
        mock_print.assert_called_with(
            "Identifier 'github.com/alice/demo' did not match any repository in config."
        )
