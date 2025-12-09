from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.changelog import generate_changelog
from pkgmgr.core.git import GitError
from pkgmgr.cli.commands.changelog import _find_previous_and_current_tag

class TestGenerateChangelog(unittest.TestCase):
    @patch("pkgmgr.actions.changelog.run_git")
    def test_generate_changelog_default_range_no_merges(self, mock_run_git) -> None:
        """
        Default behaviour:
        - to_ref = HEAD
        - from_ref = None
        - include_merges = False -> adds --no-merges
        """
        mock_run_git.return_value = "abc123 (HEAD -> main) Initial commit"

        output = generate_changelog(cwd="/repo")

        self.assertEqual(
            output,
            "abc123 (HEAD -> main) Initial commit",
        )
        mock_run_git.assert_called_once()
        args, kwargs = mock_run_git.call_args

        # Command must start with git log and include our pretty format.
        self.assertEqual(args[0][0], "log")
        self.assertIn("--pretty=format:%h %d %s", args[0])
        self.assertIn("--no-merges", args[0])
        self.assertIn("HEAD", args[0])
        self.assertEqual(kwargs.get("cwd"), "/repo")

    @patch("pkgmgr.actions.changelog.run_git")
    def test_generate_changelog_with_range_and_merges(self, mock_run_git) -> None:
        """
        Explicit range and include_merges=True:
        - from_ref/to_ref are combined into from..to
        - no --no-merges flag
        """
        mock_run_git.return_value = "def456 (tag: v1.1.0) Some change"

        output = generate_changelog(
            cwd="/repo",
            from_ref="v1.0.0",
            to_ref="v1.1.0",
            include_merges=True,
        )

        self.assertEqual(output, "def456 (tag: v1.1.0) Some change")
        mock_run_git.assert_called_once()
        args, kwargs = mock_run_git.call_args

        cmd = args[0]
        self.assertEqual(cmd[0], "log")
        self.assertIn("--pretty=format:%h %d %s", cmd)
        # include_merges=True -> no --no-merges flag
        self.assertNotIn("--no-merges", cmd)
        # Range must be exactly v1.0.0..v1.1.0
        self.assertIn("v1.0.0..v1.1.0", cmd)
        self.assertEqual(kwargs.get("cwd"), "/repo")

    @patch("pkgmgr.actions.changelog.run_git")
    def test_generate_changelog_giterror_returns_error_message(self, mock_run_git) -> None:
        """
        If Git fails, we do NOT raise; instead we return a human readable error string.
        """
        mock_run_git.side_effect = GitError("simulated git failure")

        result = generate_changelog(cwd="/repo", from_ref="v0.1.0", to_ref="v0.2.0")

        self.assertIn("[ERROR] Failed to generate changelog", result)
        self.assertIn("simulated git failure", result)
        self.assertIn("v0.1.0..v0.2.0", result)

    @patch("pkgmgr.actions.changelog.run_git")
    def test_generate_changelog_empty_output_returns_info(self, mock_run_git) -> None:
        """
        Empty git log output -> informational message instead of empty string.
        """
        mock_run_git.return_value = "   \n   "

        result = generate_changelog(cwd="/repo", from_ref=None, to_ref="HEAD")

        self.assertIn("[INFO] No commits found for range 'HEAD'", result)


class TestFindPreviousAndCurrentTag(unittest.TestCase):
    def test_no_semver_tags_returns_none_none(self) -> None:
        tags = ["foo", "bar", "v1.2", "v1.2.3.4"]  # all invalid for SemVer
        prev_tag, cur_tag = _find_previous_and_current_tag(tags)

        self.assertIsNone(prev_tag)
        self.assertIsNone(cur_tag)

    def test_latest_tags_when_no_target_given(self) -> None:
        """
        When no target tag is given, the function should return:
        (second_latest_semver_tag, latest_semver_tag)
        based on semantic version ordering, not lexicographic order.
        """
        tags = ["v1.0.0", "v1.2.0", "v1.1.0", "not-a-tag"]
        prev_tag, cur_tag = _find_previous_and_current_tag(tags)

        self.assertEqual(prev_tag, "v1.1.0")
        self.assertEqual(cur_tag, "v1.2.0")

    def test_single_semver_tag_returns_none_and_that_tag(self) -> None:
        tags = ["v0.1.0"]
        prev_tag, cur_tag = _find_previous_and_current_tag(tags)

        self.assertIsNone(prev_tag)
        self.assertEqual(cur_tag, "v0.1.0")

    def test_with_target_tag_in_the_middle(self) -> None:
        tags = ["v1.0.0", "v1.1.0", "v1.2.0"]
        prev_tag, cur_tag = _find_previous_and_current_tag(tags, target_tag="v1.1.0")

        self.assertEqual(prev_tag, "v1.0.0")
        self.assertEqual(cur_tag, "v1.1.0")

    def test_with_target_tag_first_has_no_previous(self) -> None:
        tags = ["v1.0.0", "v1.1.0"]
        prev_tag, cur_tag = _find_previous_and_current_tag(tags, target_tag="v1.0.0")

        self.assertIsNone(prev_tag)
        self.assertEqual(cur_tag, "v1.0.0")

    def test_unknown_target_tag_returns_none_none(self) -> None:
        tags = ["v1.0.0", "v1.1.0"]
        prev_tag, cur_tag = _find_previous_and_current_tag(tags, target_tag="v2.0.0")

        self.assertIsNone(prev_tag)
        self.assertIsNone(cur_tag)


if __name__ == "__main__":
    unittest.main()
