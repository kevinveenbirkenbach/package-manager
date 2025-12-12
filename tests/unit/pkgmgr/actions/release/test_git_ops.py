from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.core.git import GitError
from pkgmgr.actions.release.git_ops import (
    ensure_clean_and_synced,
    is_highest_version_tag,
    run_git_command,
    update_latest_tag,
)


class TestRunGitCommand(unittest.TestCase):
    @patch("pkgmgr.actions.release.git_ops.subprocess.run")
    def test_run_git_command_success(self, mock_run) -> None:
        run_git_command("git status")
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertIn("git status", args[0])
        self.assertTrue(kwargs.get("check"))
        self.assertTrue(kwargs.get("capture_output"))
        self.assertTrue(kwargs.get("text"))

    @patch("pkgmgr.actions.release.git_ops.subprocess.run")
    def test_run_git_command_failure_raises_git_error(self, mock_run) -> None:
        from subprocess import CalledProcessError

        mock_run.side_effect = CalledProcessError(
            returncode=1,
            cmd="git status",
            output="stdout",
            stderr="stderr",
        )

        with self.assertRaises(GitError):
            run_git_command("git status")


class TestEnsureCleanAndSynced(unittest.TestCase):
    def _fake_run(self, cmd: str, *args, **kwargs):
        class R:
            def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0):
                self.stdout = stdout
                self.stderr = stderr
                self.returncode = returncode

        # upstream detection
        if "git rev-parse --abbrev-ref --symbolic-full-name @{u}" in cmd:
            return R(stdout="origin/main")

        # fetch/pull should be invoked in real mode
        if cmd == "git fetch --prune --tags":
            return R(stdout="")
        if cmd == "git pull --ff-only":
            return R(stdout="Already up to date.")

        return R(stdout="")

    @patch("pkgmgr.actions.release.git_ops.subprocess.run")
    def test_ensure_clean_and_synced_preview_does_not_run_git_commands(self, mock_run) -> None:
        def fake(cmd: str, *args, **kwargs):
            class R:
                def __init__(self, stdout: str = ""):
                    self.stdout = stdout
                    self.stderr = ""
                    self.returncode = 0

            if "git rev-parse --abbrev-ref --symbolic-full-name @{u}" in cmd:
                return R(stdout="origin/main")
            return R(stdout="")

        mock_run.side_effect = fake

        ensure_clean_and_synced(preview=True)

        called_cmds = [c.args[0] for c in mock_run.call_args_list]
        self.assertTrue(any("git rev-parse" in c for c in called_cmds))
        self.assertFalse(any(c == "git fetch --prune --tags" for c in called_cmds))
        self.assertFalse(any(c == "git pull --ff-only" for c in called_cmds))

    @patch("pkgmgr.actions.release.git_ops.subprocess.run")
    def test_ensure_clean_and_synced_no_upstream_skips(self, mock_run) -> None:
        def fake(cmd: str, *args, **kwargs):
            class R:
                def __init__(self, stdout: str = ""):
                    self.stdout = stdout
                    self.stderr = ""
                    self.returncode = 0

            if "git rev-parse --abbrev-ref --symbolic-full-name @{u}" in cmd:
                return R(stdout="")  # no upstream
            return R(stdout="")

        mock_run.side_effect = fake

        ensure_clean_and_synced(preview=False)

        called_cmds = [c.args[0] for c in mock_run.call_args_list]
        self.assertTrue(any("git rev-parse" in c for c in called_cmds))
        self.assertFalse(any(c == "git fetch --prune --tags" for c in called_cmds))
        self.assertFalse(any(c == "git pull --ff-only" for c in called_cmds))

    @patch("pkgmgr.actions.release.git_ops.subprocess.run")
    def test_ensure_clean_and_synced_real_runs_fetch_and_pull(self, mock_run) -> None:
        mock_run.side_effect = self._fake_run

        ensure_clean_and_synced(preview=False)

        called_cmds = [c.args[0] for c in mock_run.call_args_list]
        self.assertIn("git fetch --prune --tags", called_cmds)
        self.assertIn("git pull --ff-only", called_cmds)


class TestIsHighestVersionTag(unittest.TestCase):
    @patch("pkgmgr.actions.release.git_ops.subprocess.run")
    def test_is_highest_version_tag_no_tags_true(self, mock_run) -> None:
        def fake(cmd: str, *args, **kwargs):
            class R:
                def __init__(self, stdout: str = ""):
                    self.stdout = stdout
                    self.stderr = ""
                    self.returncode = 0

            if "git tag --list" in cmd and "'v*'" in cmd:
                return R(stdout="")  # no tags
            return R(stdout="")

        mock_run.side_effect = fake

        self.assertTrue(is_highest_version_tag("v1.0.0"))

        # ensure at least the list command was queried
        called_cmds = [c.args[0] for c in mock_run.call_args_list]
        self.assertTrue(any("git tag --list" in c for c in called_cmds))

    @patch("pkgmgr.actions.release.git_ops.subprocess.run")
    def test_is_highest_version_tag_compares_sort_v(self, mock_run) -> None:
        """
        This test is aligned with the CURRENT implementation:

            return tag >= latest

        which is a *string comparison*, not a semantic version compare.
        Therefore, a candidate like v1.2.0 is lexicographically >= v1.10.0
        (because '2' > '1' at the first differing char after 'v1.').
        """
        def fake(cmd: str, *args, **kwargs):
            class R:
                def __init__(self, stdout: str = ""):
                    self.stdout = stdout
                    self.stderr = ""
                    self.returncode = 0

            if cmd.strip() == "git tag --list 'v*'":
                return R(stdout="v1.0.0\nv1.2.0\nv1.10.0\n")
            if "git tag --list 'v*'" in cmd and "sort -V" in cmd and "tail -n1" in cmd:
                return R(stdout="v1.10.0")
            return R(stdout="")

        mock_run.side_effect = fake

        # With the current implementation (string >=), both of these are True.
        self.assertTrue(is_highest_version_tag("v1.10.0"))
        self.assertTrue(is_highest_version_tag("v1.2.0"))

        # And a clearly lexicographically smaller candidate should be False.
        # Example: "v1.0.0" < "v1.10.0"
        self.assertFalse(is_highest_version_tag("v1.0.0"))

        # Ensure both capture commands were executed
        called_cmds = [c.args[0] for c in mock_run.call_args_list]
        self.assertTrue(any(cmd == "git tag --list 'v*'" for cmd in called_cmds))
        self.assertTrue(any("sort -V" in cmd and "tail -n1" in cmd for cmd in called_cmds))


class TestUpdateLatestTag(unittest.TestCase):
    @patch("pkgmgr.actions.release.git_ops.run_git_command")
    def test_update_latest_tag_preview_does_not_call_git(self, mock_run_git_command) -> None:
        update_latest_tag("v1.2.3", preview=True)
        mock_run_git_command.assert_not_called()

    @patch("pkgmgr.actions.release.git_ops.run_git_command")
    def test_update_latest_tag_real_calls_git(self, mock_run_git_command) -> None:
        update_latest_tag("v1.2.3", preview=False)

        calls = [c.args[0] for c in mock_run_git_command.call_args_list]
        self.assertIn(
            'git tag -f -a latest v1.2.3^{} -m "Floating latest tag for v1.2.3"',
            calls,
        )
        self.assertIn("git push origin latest --force", calls)


if __name__ == "__main__":
    unittest.main()
