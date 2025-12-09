from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.core.version.semver import SemVer
from pkgmgr.actions.release import release


class TestReleaseOrchestration(unittest.TestCase):
    def test_release_happy_path_uses_helpers_and_git(self) -> None:
        with patch("pkgmgr.actions.release.sys.stdin.isatty", return_value=False), \
            patch("pkgmgr.actions.release.determine_current_version") as mock_determine_current_version, \
            patch("pkgmgr.actions.release.bump_semver") as mock_bump_semver, \
            patch("pkgmgr.actions.release.update_pyproject_version") as mock_update_pyproject, \
            patch("pkgmgr.actions.release.update_changelog") as mock_update_changelog, \
            patch("pkgmgr.actions.release.get_current_branch", return_value="develop") as mock_get_current_branch, \
            patch("pkgmgr.actions.release.update_flake_version") as mock_update_flake, \
            patch("pkgmgr.actions.release.update_pkgbuild_version") as mock_update_pkgbuild, \
            patch("pkgmgr.actions.release.update_spec_version") as mock_update_spec, \
            patch("pkgmgr.actions.release.update_debian_changelog") as mock_update_debian_changelog, \
            patch("pkgmgr.actions.release.run_git_command") as mock_run_git_command, \
            patch("pkgmgr.actions.release.sync_branch_with_remote") as mock_sync_branch, \
            patch("pkgmgr.actions.release.update_latest_tag") as mock_update_latest_tag:
            mock_determine_current_version.return_value = SemVer(1, 2, 3)
            mock_bump_semver.return_value = SemVer(1, 2, 4)

            release(
                pyproject_path="pyproject.toml",
                changelog_path="CHANGELOG.md",
                release_type="patch",
                message="Test release",
                preview=False,
            )

            # Current version + bump
            mock_determine_current_version.assert_called_once()
            mock_bump_semver.assert_called_once()
            args, kwargs = mock_bump_semver.call_args
            self.assertEqual(args[0], SemVer(1, 2, 3))
            self.assertEqual(args[1], "patch")
            self.assertEqual(kwargs, {})

            # pyproject update
            mock_update_pyproject.assert_called_once()
            args, kwargs = mock_update_pyproject.call_args
            self.assertEqual(args[0], "pyproject.toml")
            self.assertEqual(args[1], "1.2.4")
            self.assertEqual(kwargs.get("preview"), False)

            # changelog update
            mock_update_changelog.assert_called_once()
            args, kwargs = mock_update_changelog.call_args
            self.assertEqual(args[0], "CHANGELOG.md")
            self.assertEqual(args[1], "1.2.4")
            self.assertEqual(kwargs.get("message"), "Test release")
            self.assertEqual(kwargs.get("preview"), False)

            # Additional packaging helpers called with preview=False
            mock_update_flake.assert_called_once()
            self.assertEqual(mock_update_flake.call_args[1].get("preview"), False)

            mock_update_pkgbuild.assert_called_once()
            self.assertEqual(mock_update_pkgbuild.call_args[1].get("preview"), False)

            mock_update_spec.assert_called_once()
            self.assertEqual(mock_update_spec.call_args[1].get("preview"), False)

            mock_update_debian_changelog.assert_called_once()
            self.assertEqual(
                mock_update_debian_changelog.call_args[1].get("preview"),
                False,
            )

            # Git operations
            mock_get_current_branch.assert_called_once()
            self.assertEqual(mock_get_current_branch.return_value, "develop")

            git_calls = [c.args[0] for c in mock_run_git_command.call_args_list]
            self.assertIn('git commit -am "Release version 1.2.4"', git_calls)
            self.assertIn('git tag -a v1.2.4 -m "Test release"', git_calls)
            self.assertIn("git push origin develop", git_calls)
            self.assertIn("git push origin --tags", git_calls)

            # Branch sync & latest tag update
            mock_sync_branch.assert_called_once_with("develop", preview=False)
            mock_update_latest_tag.assert_called_once_with("v1.2.4", preview=False)

    def test_release_preview_mode_skips_git_and_uses_preview_flag(self) -> None:
        with patch("pkgmgr.actions.release.determine_current_version") as mock_determine_current_version, \
            patch("pkgmgr.actions.release.bump_semver") as mock_bump_semver, \
            patch("pkgmgr.actions.release.update_pyproject_version") as mock_update_pyproject, \
            patch("pkgmgr.actions.release.update_changelog") as mock_update_changelog, \
            patch("pkgmgr.actions.release.get_current_branch", return_value="develop") as mock_get_current_branch, \
            patch("pkgmgr.actions.release.update_flake_version") as mock_update_flake, \
            patch("pkgmgr.actions.release.update_pkgbuild_version") as mock_update_pkgbuild, \
            patch("pkgmgr.actions.release.update_spec_version") as mock_update_spec, \
            patch("pkgmgr.actions.release.update_debian_changelog") as mock_update_debian_changelog, \
            patch("pkgmgr.actions.release.run_git_command") as mock_run_git_command, \
            patch("pkgmgr.actions.release.sync_branch_with_remote") as mock_sync_branch, \
            patch("pkgmgr.actions.release.update_latest_tag") as mock_update_latest_tag:
            mock_determine_current_version.return_value = SemVer(1, 2, 3)
            mock_bump_semver.return_value = SemVer(1, 2, 4)

            release(
                pyproject_path="pyproject.toml",
                changelog_path="CHANGELOG.md",
                release_type="patch",
                message="Preview release",
                preview=True,
            )

            # All update helpers must be called with preview=True
            mock_update_pyproject.assert_called_once()
            self.assertTrue(mock_update_pyproject.call_args[1].get("preview"))

            mock_update_changelog.assert_called_once()
            self.assertTrue(mock_update_changelog.call_args[1].get("preview"))

            mock_update_flake.assert_called_once()
            self.assertTrue(mock_update_flake.call_args[1].get("preview"))

            mock_update_pkgbuild.assert_called_once()
            self.assertTrue(mock_update_pkgbuild.call_args[1].get("preview"))

            mock_update_spec.assert_called_once()
            self.assertTrue(mock_update_spec.call_args[1].get("preview"))

            mock_update_debian_changelog.assert_called_once()
            self.assertTrue(mock_update_debian_changelog.call_args[1].get("preview"))

            # In preview mode no real git commands must be executed
            mock_run_git_command.assert_not_called()

            # Branch sync is still invoked (with preview=True internally),
            # and latest tag is only announced in preview mode
            mock_sync_branch.assert_called_once_with("develop", preview=True)
            mock_update_latest_tag.assert_called_once_with("v1.2.4", preview=True)


if __name__ == "__main__":
    unittest.main()
