import unittest
from unittest.mock import patch

from pkgmgr.actions.publish.workflow import publish


class TestPublishWorkflowPreview(unittest.TestCase):
    @patch("pkgmgr.actions.publish.workflow.read_mirrors_file")
    @patch("pkgmgr.actions.publish.workflow.head_semver_tags")
    def test_preview_does_not_build(self, mock_tags, mock_mirrors):
        mock_mirrors.return_value = {"pypi": "https://pypi.org/project/example/"}
        mock_tags.return_value = ["v1.0.0"]

        publish(
            repo={},
            repo_dir=".",
            preview=True,
        )
