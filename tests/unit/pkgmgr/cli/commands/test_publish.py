import unittest
from unittest.mock import patch

from pkgmgr.cli.commands.publish import handle_publish


class TestHandlePublish(unittest.TestCase):
    @patch("pkgmgr.cli.commands.publish.publish")
    def test_no_selected_repos(self, mock_publish):
        handle_publish(args=object(), ctx=None, selected=[])
        mock_publish.assert_not_called()
