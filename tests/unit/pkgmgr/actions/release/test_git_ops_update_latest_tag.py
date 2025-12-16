from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.release.git_ops import update_latest_tag


class TestUpdateLatestTag(unittest.TestCase):
    @patch("pkgmgr.actions.release.git_ops.push")
    @patch("pkgmgr.actions.release.git_ops.tag_force_annotated")
    def test_preview_calls_commands_with_preview_true(
        self,
        mock_tag_force_annotated,
        mock_push,
    ) -> None:
        update_latest_tag("v1.2.3", preview=True)

        mock_tag_force_annotated.assert_called_once_with(
            name="latest",
            target="v1.2.3^{}",
            message="Floating latest tag for v1.2.3",
            preview=True,
        )
        mock_push.assert_called_once_with(
            "origin",
            "latest",
            force=True,
            preview=True,
        )

    @patch("pkgmgr.actions.release.git_ops.push")
    @patch("pkgmgr.actions.release.git_ops.tag_force_annotated")
    def test_real_calls_commands_with_preview_false(
        self,
        mock_tag_force_annotated,
        mock_push,
    ) -> None:
        update_latest_tag("v1.2.3", preview=False)

        mock_tag_force_annotated.assert_called_once_with(
            name="latest",
            target="v1.2.3^{}",
            message="Floating latest tag for v1.2.3",
            preview=False,
        )
        mock_push.assert_called_once_with(
            "origin",
            "latest",
            force=True,
            preview=False,
        )
