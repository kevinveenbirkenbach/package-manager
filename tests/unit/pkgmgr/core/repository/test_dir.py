import unittest
from unittest.mock import patch

from pkgmgr.core.repository.dir import get_repo_dir


class TestGetRepoDir(unittest.TestCase):
    def test_builds_path_with_expanded_base_dir(self):
        repo = {"provider": "github.com", "account": "alice", "repository": "demo"}
        with patch("pkgmgr.core.repository.dir.os.path.expanduser", return_value="/home/u/repos"):
            result = get_repo_dir("~/repos", repo)

        self.assertEqual(result, "/home/u/repos/github.com/alice/demo")

    def test_exits_with_code_3_if_base_dir_is_none(self):
        repo = {"provider": "github.com", "account": "alice", "repository": "demo"}
        with self.assertRaises(SystemExit) as ctx:
            get_repo_dir(None, repo)  # type: ignore[arg-type]

        self.assertEqual(ctx.exception.code, 3)

    def test_exits_with_code_3_if_repo_is_invalid_type(self):
        with self.assertRaises(SystemExit) as ctx:
            get_repo_dir("/repos", None)  # type: ignore[arg-type]

        self.assertEqual(ctx.exception.code, 3)
