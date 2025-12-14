
import unittest
from unittest.mock import patch

from pkgmgr.actions.publish.git_tags import head_semver_tags


class TestHeadSemverTags(unittest.TestCase):
    @patch("pkgmgr.actions.publish.git_tags.run_git")
    def test_no_tags(self, mock_run_git):
        mock_run_git.return_value = ""
        self.assertEqual(head_semver_tags(), [])

    @patch("pkgmgr.actions.publish.git_tags.run_git")
    def test_filters_and_sorts_semver(self, mock_run_git):
        mock_run_git.return_value = "v1.0.0\nv2.0.0\nfoo\n"
        self.assertEqual(
            head_semver_tags(),
            ["v1.0.0", "v2.0.0"],
        )
