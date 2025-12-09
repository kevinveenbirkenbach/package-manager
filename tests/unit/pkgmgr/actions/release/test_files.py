from __future__ import annotations

import os
import tempfile
import textwrap
import unittest
from unittest.mock import patch

from pkgmgr.actions.release.files import (
    update_pyproject_version,
    update_flake_version,
    update_pkgbuild_version,
    update_spec_version,
    update_changelog,
    update_debian_changelog,
)


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


if __name__ == "__main__":
    unittest.main()
