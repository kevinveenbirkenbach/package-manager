#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest
from unittest.mock import patch

from pkgmgr.core.git.errors import GitRunError
from pkgmgr.core.git.run import run
from pkgmgr.core.git.queries import get_tags, get_head_commit, get_current_branch


class TestGitRun(unittest.TestCase):
    @patch("pkgmgr.core.git.run.subprocess.run")
    def test_run_success(self, mock_run):
        mock_run.return_value.stdout = "ok\n"
        mock_run.return_value.stderr = ""
        mock_run.return_value.returncode = 0

        output = run(["status"], cwd="/tmp/repo")

        self.assertEqual(output, "ok")
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0][0], "git")
        self.assertEqual(kwargs.get("cwd"), "/tmp/repo")

    @patch("pkgmgr.core.git.run.subprocess.run")
    def test_run_failure_raises_giterror(self, mock_run):
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["git", "status"],
            output="bad\n",
            stderr="error\n",
        )

        with self.assertRaises(GitRunError) as ctx:
            run(["status"], cwd="/tmp/repo")

        msg = str(ctx.exception)
        self.assertIn("Git command failed", msg)
        self.assertIn("Exit code: 1", msg)
        self.assertIn("bad", msg)
        self.assertIn("error", msg)


class TestGitQueries(unittest.TestCase):
    @patch("pkgmgr.core.git.queries.get_tags.run")
    def test_get_tags_empty(self, mock_run):
        mock_run.return_value = ""
        tags = get_tags(cwd="/tmp/repo")
        self.assertEqual(tags, [])

    @patch("pkgmgr.core.git.queries.get_tags.run")
    def test_get_tags_non_empty(self, mock_run):
        mock_run.return_value = "v1.0.0\nv1.1.0\n"
        tags = get_tags(cwd="/tmp/repo")
        self.assertEqual(tags, ["v1.0.0", "v1.1.0"])

    @patch("pkgmgr.core.git.queries.get_head_commit.run")
    def test_get_head_commit_success(self, mock_run):
        mock_run.return_value = "abc123"
        commit = get_head_commit(cwd="/tmp/repo")
        self.assertEqual(commit, "abc123")

    @patch("pkgmgr.core.git.queries.get_head_commit.run")
    def test_get_head_commit_failure_returns_none(self, mock_run):
        mock_run.side_effect = GitRunError("fail")
        commit = get_head_commit(cwd="/tmp/repo")
        self.assertIsNone(commit)

    @patch("pkgmgr.core.git.queries.get_current_branch.run")
    def test_get_current_branch_success(self, mock_run):
        mock_run.return_value = "main"
        branch = get_current_branch(cwd="/tmp/repo")
        self.assertEqual(branch, "main")

    @patch("pkgmgr.core.git.queries.get_current_branch.run")
    def test_get_current_branch_failure_returns_none(self, mock_run):
        mock_run.side_effect = GitRunError("fail")
        branch = get_current_branch(cwd="/tmp/repo")
        self.assertIsNone(branch)


if __name__ == "__main__":
    unittest.main()
