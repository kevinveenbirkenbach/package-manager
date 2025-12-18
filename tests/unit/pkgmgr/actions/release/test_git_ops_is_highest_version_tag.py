from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.release.git_ops import is_highest_version_tag


class TestIsHighestVersionTag(unittest.TestCase):
    @patch("pkgmgr.actions.release.git_ops.list_tags")
    def test_no_tags_returns_true(self, mock_list_tags) -> None:
        mock_list_tags.return_value = []
        self.assertTrue(is_highest_version_tag("v1.0.0"))
        mock_list_tags.assert_called_once_with("v*")

    @patch("pkgmgr.actions.release.git_ops.list_tags")
    def test_parseable_semver_compares_correctly(self, mock_list_tags) -> None:
        # Highest is v1.10.0 (semantic compare)
        mock_list_tags.return_value = ["v1.0.0", "v1.2.0", "v1.10.0"]

        self.assertTrue(is_highest_version_tag("v1.10.0"))
        self.assertFalse(is_highest_version_tag("v1.2.0"))
        self.assertFalse(is_highest_version_tag("v1.0.0"))

    @patch("pkgmgr.actions.release.git_ops.list_tags")
    def test_ignores_non_parseable_v_tags_for_semver_compare(
        self, mock_list_tags
    ) -> None:
        mock_list_tags.return_value = ["v1.2.0", "v1.10.0", "v1.2.0-rc1", "vfoo"]

        self.assertTrue(is_highest_version_tag("v1.10.0"))
        self.assertFalse(is_highest_version_tag("v1.2.0"))

    @patch("pkgmgr.actions.release.git_ops.list_tags")
    def test_current_tag_not_parseable_falls_back_to_lex_compare(
        self, mock_list_tags
    ) -> None:
        mock_list_tags.return_value = ["v1.9.0", "v1.10.0"]

        # prerelease must NOT outrank the final release
        self.assertFalse(is_highest_version_tag("v1.10.0-rc1"))
        self.assertFalse(is_highest_version_tag("v1.0.0-rc1"))
