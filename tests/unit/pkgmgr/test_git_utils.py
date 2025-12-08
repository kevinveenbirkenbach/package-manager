#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pkgmgr.git_utils import (
    GitError,
    run_git,
    get_tags,
    get_head_commit,
    get_current_branch,
)


class TestGitUtils(unittest.TestCase):
    @patch("pkgmgr.git_utils.subprocess.run")
    def test_run_git_success(self, mock_run):
        mock_run.return_value = SimpleNamespace(
            stdout="ok\n",
            stderr="",
            returncode=0,
        )

        output = run_git(["status"], cwd="/tmp/repo")

        self.assertEqual(output, "ok")
        mock_run.assert_called_once()
        # basic sanity: command prefix should be 'git'
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0][0], "git")
        self.assertEqual(kwargs.get("cwd"), "/tmp/repo")

    @patch("pkgmgr.git_utils.subprocess.run")
    def test_run_git_failure_raises_giterror(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["git", "status"],
            output="bad\n",
            stderr="error\n",
        )

        with self.assertRaises(GitError) as ctx:
            run_git(["status"], cwd="/tmp/repo")

        msg = str(ctx.exception)
        self.assertIn("Git command failed", msg)
        self.assertIn("Exit code: 1", msg)
        self.assertIn("bad", msg)
        self.assertIn("error", msg)

    @patch("pkgmgr.git_utils.subprocess.run")
    def test_get_tags_empty(self, mock_run):
        mock_run.return_value = SimpleNamespace(
            stdout="",
            stderr="",
            returncode=0,
        )

        tags = get_tags(cwd="/tmp/repo")
        self.assertEqual(tags, [])

    @patch("pkgmgr.git_utils.subprocess.run")
    def test_get_tags_non_empty(self, mock_run):
        mock_run.return_value = SimpleNamespace(
            stdout="v1.0.0\nv1.1.0\n",
            stderr="",
            returncode=0,
        )

        tags = get_tags(cwd="/tmp/repo")
        self.assertEqual(tags, ["v1.0.0", "v1.1.0"])

    @patch("pkgmgr.git_utils.subprocess.run")
    def test_get_head_commit_success(self, mock_run):
        mock_run.return_value = SimpleNamespace(
            stdout="abc123\n",
            stderr="",
            returncode=0,
        )

        commit = get_head_commit(cwd="/tmp/repo")
        self.assertEqual(commit, "abc123")

    @patch("pkgmgr.git_utils.subprocess.run")
    def test_get_head_commit_failure_returns_none(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["git", "rev-parse", "HEAD"],
            output="",
            stderr="error\n",
        )

        commit = get_head_commit(cwd="/tmp/repo")
        self.assertIsNone(commit)

    @patch("pkgmgr.git_utils.subprocess.run")
    def test_get_current_branch_success(self, mock_run):
        mock_run.return_value = SimpleNamespace(
            stdout="main\n",
            stderr="",
            returncode=0,
        )

        branch = get_current_branch(cwd="/tmp/repo")
        self.assertEqual(branch, "main")

    @patch("pkgmgr.git_utils.subprocess.run")
    def test_get_current_branch_failure_returns_none(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(
            returncode=1,
            cmd=["git", "rev-parse", "--abbrev-ref", "HEAD"],
            output="",
            stderr="error\n",
        )

        branch = get_current_branch(cwd="/tmp/repo")
        self.assertIsNone(branch)


if __name__ == "__main__":
    unittest.main()
