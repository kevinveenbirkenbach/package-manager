from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.core.version.semver import SemVer
from pkgmgr.actions.release.versioning import (
    determine_current_version,
    bump_semver,
)


class TestDetermineCurrentVersion(unittest.TestCase):
    @patch("pkgmgr.actions.release.versioning.get_tags", return_value=[])
    def test_determine_current_version_no_tags_returns_zero(
        self,
        mock_get_tags,
    ) -> None:
        ver = determine_current_version()
        self.assertIsInstance(ver, SemVer)
        self.assertEqual((ver.major, ver.minor, ver.patch), (0, 0, 0))
        mock_get_tags.assert_called_once()

    @patch("pkgmgr.actions.release.versioning.find_latest_version")
    @patch("pkgmgr.actions.release.versioning.get_tags")
    def test_determine_current_version_uses_latest_semver_tag(
        self,
        mock_get_tags,
        mock_find_latest_version,
    ) -> None:
        mock_get_tags.return_value = ["v0.1.0", "v1.2.3"]
        mock_find_latest_version.return_value = ("v1.2.3", SemVer(1, 2, 3))

        ver = determine_current_version()

        self.assertEqual((ver.major, ver.minor, ver.patch), (1, 2, 3))
        mock_get_tags.assert_called_once()
        mock_find_latest_version.assert_called_once_with(["v0.1.0", "v1.2.3"])


class TestBumpSemVer(unittest.TestCase):
    def test_bump_semver_major(self) -> None:
        base = SemVer(1, 2, 3)
        bumped = bump_semver(base, "major")
        self.assertEqual((bumped.major, bumped.minor, bumped.patch), (2, 0, 0))

    def test_bump_semver_minor(self) -> None:
        base = SemVer(1, 2, 3)
        bumped = bump_semver(base, "minor")
        self.assertEqual((bumped.major, bumped.minor, bumped.patch), (1, 3, 0))

    def test_bump_semver_patch(self) -> None:
        base = SemVer(1, 2, 3)
        bumped = bump_semver(base, "patch")
        self.assertEqual((bumped.major, bumped.minor, bumped.patch), (1, 2, 4))

    def test_bump_semver_invalid_type_raises(self) -> None:
        base = SemVer(1, 2, 3)
        with self.assertRaises(ValueError):
            bump_semver(base, "invalid-type")


if __name__ == "__main__":
    unittest.main()
