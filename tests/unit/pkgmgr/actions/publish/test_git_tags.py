import unittest
from unittest.mock import patch

from pkgmgr.actions.publish.git_tags import head_semver_tags


class TestHeadSemverTags(unittest.TestCase):
    @patch("pkgmgr.actions.publish.git_tags.get_tags_at_ref", return_value=[])
    def test_no_tags(self, _mock_get_tags_at_ref) -> None:
        self.assertEqual(head_semver_tags(), [])

    @patch("pkgmgr.actions.publish.git_tags.get_tags_at_ref", return_value=["v2.0.0", "nope", "v1.0.0", "v1.2.0"])
    def test_filters_and_sorts_semver(self, _mock_get_tags_at_ref) -> None:
        self.assertEqual(head_semver_tags(), ["v1.0.0", "v1.2.0", "v2.0.0"])
