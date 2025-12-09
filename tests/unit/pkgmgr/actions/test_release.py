from __future__ import annotations

import os
import tempfile
import textwrap
import unittest
from unittest.mock import patch

from pkgmgr.core.version.semver import SemVer
from pkgmgr.actions.release import (
    _determine_current_version,
    _bump_semver,
    update_pyproject_version,
    update_flake_version,
    update_pkgbuild_version,
    update_spec_version,
    update_changelog,
    update_debian_changelog,
    release,
)


class TestDetermineCurrentVersion(unittest.TestCase):
    @patch("pkgmgr.actions.release.get_tags", return_value=[])
    def test_determine_current_version_no_tags_returns_zero(
        self,
        mock_get_tags,
    ) -> None:
        ver = _determine_current_version()
        self.assertIsInstance(ver, SemVer)
        self.assertEqual((ver.major, ver.minor, ver.patch), (0, 0, 0))
        mock_get_tags.assert_called_once()

    @patch("pkgmgr.actions.release.find_latest_version")
    @patch("pkgmgr.actions.release.get_tags")
    def test_determine_current_version_uses_latest_semver_tag(
        self,
        mock_get_tags,
        mock_find_latest_version,
    ) -> None:
        mock_get_tags.return_value = ["v0.1.0", "v1.2.3"]
        mock_find_latest_version.return_value = ("v1.2.3", SemVer(1, 2, 3))

        ver = _determine_current_version()

        self.assertEqual((ver.major, ver.minor, ver.patch), (1, 2, 3))
        mock_get_tags.assert_called_once()
        mock_find_latest_version.assert_called_once_with(["v0.1.0", "v1.2.3"])


class TestBumpSemVer(unittest.TestCase):
    def test_bump_semver_major(self) -> None:
        base = SemVer(1, 2, 3)
        bumped = _bump_semver(base, "major")
        self.assertEqual((bumped.major, bumped.minor, bumped.patch), (2, 0, 0))

    def test_bump_semver_minor(self) -> None:
        base = SemVer(1, 2, 3)
        bumped = _bump_semver(base, "minor")
        self.assertEqual((bumped.major, bumped.minor, bumped.patch), (1, 3, 0))

    def test_bump_semver_patch(self) -> None:
        base = SemVer(1, 2, 3)
        bumped = _bump_semver(base, "patch")
        self.assertEqual((bumped.major, bumped.minor, bumped.patch), (1, 2, 4))

    def test_bump_semver_invalid_type_raises(self) -> None:
        base = SemVer(1, 2, 3)
        with self.assertRaises(ValueError):
            _bump_semver(base, "invalid-type")


class TestUpdatePyprojectVersion(unittest.TestCase):
    def test_update_pyproject_version_replaces_version_line(self) -> None:
        original = textwrap.dedent(
            """
            [project]
            name = "example"
            version = "0.1.0"
            """
        ).strip() + "\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "pyproject.toml")
            with open(path, "w", encoding="utf-8") as f:
                f.write(original)

            update_pyproject_version(path, "1.2.3", preview=False)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

        self.assertIn('version = "1.2.3"', content)
        self.assertNotIn('version = "0.1.0"', content)

    def test_update_pyproject_version_preview_does_not_write(self) -> None:
        original = textwrap.dedent(
            """
            [project]
            name = "example"
            version = "0.1.0"
            """
        ).strip() + "\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "pyproject.toml")
            with open(path, "w", encoding="utf-8") as f:
                f.write(original)

            update_pyproject_version(path, "1.2.3", preview=True)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

        # Content must be unchanged in preview mode
        self.assertEqual(content, original)

    def test_update_pyproject_version_exits_when_no_version_line_found(self) -> None:
        original = textwrap.dedent(
            """
            [project]
            name = "example"
            """
        ).strip() + "\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "pyproject.toml")
            with open(path, "w", encoding="utf-8") as f:
                f.write(original)

            with self.assertRaises(SystemExit) as cm:
                update_pyproject_version(path, "1.2.3", preview=False)

        self.assertNotEqual(cm.exception.code, 0)


class TestUpdateFlakeVersion(unittest.TestCase):
    def test_update_flake_version_normal(self) -> None:
        original = 'version = "0.1.0";\n'
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "flake.nix")
            with open(path, "w", encoding="utf-8") as f:
                f.write(original)

            update_flake_version(path, "1.2.3", preview=False)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

        self.assertIn('version = "1.2.3";', content)
        self.assertNotIn('version = "0.1.0";', content)

    def test_update_flake_version_preview(self) -> None:
        original = 'version = "0.1.0";\n'
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "flake.nix")
            with open(path, "w", encoding="utf-8") as f:
                f.write(original)

            update_flake_version(path, "1.2.3", preview=True)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

        self.assertEqual(content, original)


class TestUpdatePkgbuildVersion(unittest.TestCase):
    def test_update_pkgbuild_version_normal(self) -> None:
        original = textwrap.dedent(
            """
            pkgname=example
            pkgver=0.1.0
            pkgrel=5
            """
        ).strip() + "\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "PKGBUILD")
            with open(path, "w", encoding="utf-8") as f:
                f.write(original)

            update_pkgbuild_version(path, "1.2.3", preview=False)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

        self.assertIn("pkgver=1.2.3", content)
        self.assertIn("pkgrel=1", content)
        self.assertNotIn("pkgver=0.1.0", content)

    def test_update_pkgbuild_version_preview(self) -> None:
        original = textwrap.dedent(
            """
            pkgname=example
            pkgver=0.1.0
            pkgrel=5
            """
        ).strip() + "\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "PKGBUILD")
            with open(path, "w", encoding="utf-8") as f:
                f.write(original)

            update_pkgbuild_version(path, "1.2.3", preview=True)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

        self.assertEqual(content, original)


class TestUpdateSpecVersion(unittest.TestCase):
    def test_update_spec_version_normal(self) -> None:
        original = textwrap.dedent(
            """
            Name: package-manager
            Version: 0.1.0
            Release: 5%{?dist}
            """
        ).strip() + "\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "package-manager.spec")
            with open(path, "w", encoding="utf-8") as f:
                f.write(original)

            update_spec_version(path, "1.2.3", preview=False)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

        self.assertIn("Version: 1.2.3", content)
        self.assertIn("Release: 1%{?dist}", content)
        self.assertNotIn("Version: 0.1.0", content)
        self.assertNotIn("Release: 5%{?dist}", content)

    def test_update_spec_version_preview(self) -> None:
        original = textwrap.dedent(
            """
            Name: package-manager
            Version: 0.1.0
            Release: 5%{?dist}
            """
        ).strip() + "\n"

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "package-manager.spec")
            with open(path, "w", encoding="utf-8") as f:
                f.write(original)

            update_spec_version(path, "1.2.3", preview=True)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

        self.assertEqual(content, original)


class TestUpdateChangelog(unittest.TestCase):
    def test_update_changelog_creates_file_if_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "CHANGELOG.md")
            self.assertFalse(os.path.exists(path))

            update_changelog(path, "1.2.3", message="First release", preview=False)

            self.assertTrue(os.path.exists(path))
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

        self.assertIn("## [1.2.3]", content)
        self.assertIn("First release", content)

    def test_update_changelog_prepends_entry_to_existing_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "CHANGELOG.md")
            with open(path, "w", encoding="utf-8") as f:
                f.write("## [0.1.0] - 2024-01-01\n\n* Initial content\n")

            update_changelog(path, "1.0.0", message=None, preview=False)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

        # New entry must be on top
        self.assertTrue(content.startswith("## [1.0.0]"))
        self.assertIn("## [0.1.0] - 2024-01-01", content)

    def test_update_changelog_preview_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "CHANGELOG.md")
            original = "## [0.1.0] - 2024-01-01\n\n* Initial content\n"
            with open(path, "w", encoding="utf-8") as f:
                f.write(original)

            update_changelog(path, "1.0.0", message="Preview only", preview=True)

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

        self.assertEqual(content, original)


class TestUpdateDebianChangelog(unittest.TestCase):
    def test_update_debian_changelog_creates_new_stanza(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "changelog")
            # existing content
            with open(path, "w", encoding="utf-8") as f:
                f.write("existing content\n")

            with patch.dict(
                os.environ,
                {
                    "DEBFULLNAME": "Test Maintainer",
                    "DEBEMAIL": "test@example.com",
                },
                clear=False,
            ):
                update_debian_changelog(
                    debian_changelog_path=path,
                    package_name="package-manager",
                    new_version="1.2.3",
                    message="Test debian entry",
                    preview=False,
                )

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

        self.assertIn("package-manager (1.2.3-1) unstable; urgency=medium", content)
        self.assertIn("  * Test debian entry", content)
        self.assertIn("Test Maintainer <test@example.com>", content)
        self.assertIn("existing content", content)

    def test_update_debian_changelog_preview_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "changelog")
            original = "existing content\n"
            with open(path, "w", encoding="utf-8") as f:
                f.write(original)

            with patch.dict(
                os.environ,
                {
                    "DEBFULLNAME": "Test Maintainer",
                    "DEBEMAIL": "test@example.com",
                },
                clear=False,
            ):
                update_debian_changelog(
                    debian_changelog_path=path,
                    package_name="package-manager",
                    new_version="1.2.3",
                    message="Test debian entry",
                    preview=True,
                )

            with open(path, "r", encoding="utf-8") as f:
                content = f.read()

        self.assertEqual(content, original)


class TestReleaseOrchestration(unittest.TestCase):
    @patch("pkgmgr.actions.release.sys.stdin.isatty", return_value=False)
    @patch("pkgmgr.actions.release._run_git_command")
    @patch("pkgmgr.actions.release.update_debian_changelog")
    @patch("pkgmgr.actions.release.update_spec_version")
    @patch("pkgmgr.actions.release.update_pkgbuild_version")
    @patch("pkgmgr.actions.release.update_flake_version")
    @patch("pkgmgr.actions.release.get_current_branch", return_value="develop")
    @patch("pkgmgr.actions.release.update_changelog")
    @patch("pkgmgr.actions.release.update_pyproject_version")
    @patch("pkgmgr.actions.release._bump_semver")
    @patch("pkgmgr.actions.release._determine_current_version")
    def test_release_happy_path_uses_helpers_and_git(
        self,
        mock_determine_current_version,
        mock_bump_semver,
        mock_update_pyproject,
        mock_update_changelog,
        mock_get_current_branch,
        mock_update_flake,
        mock_update_pkgbuild,
        mock_update_spec,
        mock_update_debian_changelog,
        mock_run_git_command,
        mock_isatty,
    ) -> None:
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

        # repo root is derived from pyproject path; we don't care about
        # exact paths here, only that helpers are called with preview=False.
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

    @patch("pkgmgr.actions.release.sys.stdin.isatty", return_value=False)
    @patch("pkgmgr.actions.release._run_git_command")
    @patch("pkgmgr.actions.release.update_debian_changelog")
    @patch("pkgmgr.actions.release.update_spec_version")
    @patch("pkgmgr.actions.release.update_pkgbuild_version")
    @patch("pkgmgr.actions.release.update_flake_version")
    @patch("pkgmgr.actions.release.get_current_branch", return_value="develop")
    @patch("pkgmgr.actions.release.update_changelog")
    @patch("pkgmgr.actions.release.update_pyproject_version")
    @patch("pkgmgr.actions.release._bump_semver")
    @patch("pkgmgr.actions.release._determine_current_version")
    def test_release_preview_mode_skips_git_and_uses_preview_flag(
        self,
        mock_determine_current_version,
        mock_bump_semver,
        mock_update_pyproject,
        mock_update_changelog,
        mock_get_current_branch,
        mock_update_flake,
        mock_update_pkgbuild,
        mock_update_spec,
        mock_update_debian_changelog,
        mock_run_git_command,
        mock_isatty,
    ) -> None:
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

        # In preview mode no git commands must be executed
        mock_run_git_command.assert_not_called()


if __name__ == "__main__":
    unittest.main()
