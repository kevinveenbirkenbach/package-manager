from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import patch


class TestResolveRepositoryPath(unittest.TestCase):
    def test_explicit_directory_key_wins(self) -> None:
        from pkgmgr.cli.tools.paths import resolve_repository_path

        ctx = SimpleNamespace(repositories_base_dir="/base", repositories_dir="/base2")
        repo = {"directory": "/explicit/repo"}

        self.assertEqual(resolve_repository_path(repo, ctx), "/explicit/repo")

    def test_fallback_uses_get_repo_dir_with_repositories_base_dir(self) -> None:
        from pkgmgr.cli.tools.paths import resolve_repository_path

        ctx = SimpleNamespace(repositories_base_dir="/base", repositories_dir="/base2")
        repo = {"provider": "github.com", "account": "acme", "repository": "demo"}

        with patch(
            "pkgmgr.cli.tools.paths.get_repo_dir", return_value="/computed/repo"
        ) as m:
            out = resolve_repository_path(repo, ctx)

        self.assertEqual(out, "/computed/repo")
        m.assert_called_once_with("/base", repo)

    def test_raises_if_no_base_dir_in_context(self) -> None:
        from pkgmgr.cli.tools.paths import resolve_repository_path

        ctx = SimpleNamespace(repositories_base_dir=None, repositories_dir=None)
        repo = {"provider": "github.com", "account": "acme", "repository": "demo"}

        with self.assertRaises(RuntimeError) as cm:
            resolve_repository_path(repo, ctx)

        self.assertIn("Cannot resolve repositories base directory", str(cm.exception))
