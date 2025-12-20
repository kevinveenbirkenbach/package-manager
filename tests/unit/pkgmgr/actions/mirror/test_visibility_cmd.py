# tests/unit/pkgmgr/actions/mirror/test_visibility_cmd.py
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch, MagicMock

from pkgmgr.actions.mirror.visibility_cmd import set_mirror_visibility


class TestMirrorVisibilityCmd(unittest.TestCase):
    def test_invalid_visibility_raises_value_error(self) -> None:
        with self.assertRaises(ValueError):
            set_mirror_visibility(
                selected_repos=[{"id": "x"}],
                repositories_base_dir="/tmp",
                all_repos=[],
                visibility="nope",
            )

    @patch("pkgmgr.actions.mirror.visibility_cmd.build_context")
    @patch("pkgmgr.actions.mirror.visibility_cmd.determine_primary_remote_url")
    def test_no_git_mirrors_and_no_primary_prints_nothing_to_do(
        self,
        mock_determine_primary: MagicMock,
        mock_build_ctx: MagicMock,
    ) -> None:
        ctx = MagicMock()
        ctx.identifier = "repo1"
        ctx.repo_dir = "/tmp/repo1"
        ctx.resolved_mirrors = {"pypi": "https://pypi.org/project/x/"}  # non-git
        mock_build_ctx.return_value = ctx
        mock_determine_primary.return_value = None

        buf = io.StringIO()
        with redirect_stdout(buf):
            set_mirror_visibility(
                selected_repos=[{"id": "repo1", "description": "desc"}],
                repositories_base_dir="/tmp",
                all_repos=[],
                visibility="public",
                preview=True,
            )

        out = buf.getvalue()
        self.assertIn("[MIRROR VISIBILITY] repo1", out)
        self.assertIn("Nothing to do.", out)

    @patch("pkgmgr.actions.mirror.visibility_cmd.build_context")
    @patch("pkgmgr.actions.mirror.visibility_cmd.determine_primary_remote_url")
    @patch("pkgmgr.actions.mirror.visibility_cmd.normalize_provider_host")
    @patch("pkgmgr.actions.mirror.visibility_cmd.parse_repo_from_git_url")
    @patch("pkgmgr.actions.mirror.visibility_cmd.set_repo_visibility")
    def test_applies_to_primary_when_no_git_mirrors(
        self,
        mock_set_repo_visibility: MagicMock,
        mock_parse: MagicMock,
        mock_norm: MagicMock,
        mock_determine_primary: MagicMock,
        mock_build_ctx: MagicMock,
    ) -> None:
        ctx = MagicMock()
        ctx.identifier = "repo1"
        ctx.repo_dir = "/tmp/repo1"
        ctx.resolved_mirrors = {}  # no mirrors
        mock_build_ctx.return_value = ctx

        primary = "ssh://git.veen.world:2201/me/repo1.git"
        mock_determine_primary.return_value = primary

        mock_parse.return_value = ("git.veen.world:2201", "me", "repo1")
        mock_norm.return_value = "git.veen.world:2201"

        mock_set_repo_visibility.return_value = MagicMock(
            status="skipped", message="Preview"
        )

        buf = io.StringIO()
        with redirect_stdout(buf):
            set_mirror_visibility(
                selected_repos=[{"id": "repo1", "description": "desc"}],
                repositories_base_dir="/tmp",
                all_repos=[],
                visibility="private",
                preview=True,
            )

        mock_set_repo_visibility.assert_called_once()
        _, kwargs = mock_set_repo_visibility.call_args
        self.assertEqual(
            kwargs["private"], True
        )  # visibility=private => desired_private=True
        out = buf.getvalue()
        self.assertIn("applying to primary", out)

    @patch("pkgmgr.actions.mirror.visibility_cmd.build_context")
    @patch("pkgmgr.actions.mirror.visibility_cmd.normalize_provider_host")
    @patch("pkgmgr.actions.mirror.visibility_cmd.parse_repo_from_git_url")
    @patch("pkgmgr.actions.mirror.visibility_cmd.set_repo_visibility")
    def test_applies_to_all_git_mirrors(
        self,
        mock_set_repo_visibility: MagicMock,
        mock_parse: MagicMock,
        mock_norm: MagicMock,
        mock_build_ctx: MagicMock,
    ) -> None:
        ctx = MagicMock()
        ctx.identifier = "repo1"
        ctx.repo_dir = "/tmp/repo1"
        ctx.resolved_mirrors = {
            "origin": "ssh://git.veen.world:2201/me/repo1.git",
            "backup": "git@git.veen.world:me/repo1.git",
            "notgit": "https://pypi.org/project/x/",
        }
        mock_build_ctx.return_value = ctx

        # For both URLs, parsing returns same repo
        mock_parse.return_value = ("git.veen.world", "me", "repo1")
        mock_norm.return_value = "git.veen.world"

        mock_set_repo_visibility.return_value = MagicMock(
            status="noop", message="Already public"
        )

        buf = io.StringIO()
        with redirect_stdout(buf):
            set_mirror_visibility(
                selected_repos=[{"id": "repo1", "description": "desc"}],
                repositories_base_dir="/tmp",
                all_repos=[],
                visibility="public",
                preview=False,
            )

        # Should be called for origin + backup (2), but not for notgit
        self.assertEqual(mock_set_repo_visibility.call_count, 2)

        # Each call should request desired private=False for "public"
        for call in mock_set_repo_visibility.call_args_list:
            _, kwargs = call
            self.assertEqual(kwargs["private"], False)

        out = buf.getvalue()
        self.assertIn("applying to mirror 'origin'", out)
        self.assertIn("applying to mirror 'backup'", out)

    @patch("pkgmgr.actions.mirror.visibility_cmd.build_context")
    @patch("pkgmgr.actions.mirror.visibility_cmd.determine_primary_remote_url")
    def test_primary_not_git_prints_nothing_to_do(
        self,
        mock_determine_primary: MagicMock,
        mock_build_ctx: MagicMock,
    ) -> None:
        ctx = MagicMock()
        ctx.identifier = "repo1"
        ctx.repo_dir = "/tmp/repo1"
        ctx.resolved_mirrors = {}
        mock_build_ctx.return_value = ctx

        mock_determine_primary.return_value = "https://example.com/not-a-git-url"

        buf = io.StringIO()
        with redirect_stdout(buf):
            set_mirror_visibility(
                selected_repos=[{"id": "repo1"}],
                repositories_base_dir="/tmp",
                all_repos=[],
                visibility="public",
            )

        out = buf.getvalue()
        self.assertIn("Nothing to do.", out)


if __name__ == "__main__":
    unittest.main()
