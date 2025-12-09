#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import unittest

from pkgmgr.core.version.semver import (
    SemVer,
    is_semver_tag,
    extract_semver_from_tags,
    find_latest_version,
    bump_major,
    bump_minor,
    bump_patch,
)


class TestSemVer(unittest.TestCase):
    def test_semver_parse_basic(self):
        ver = SemVer.parse("1.2.3")
        self.assertEqual(ver.major, 1)
        self.assertEqual(ver.minor, 2)
        self.assertEqual(ver.patch, 3)

    def test_semver_parse_with_v_prefix(self):
        ver = SemVer.parse("v10.20.30")
        self.assertEqual(ver.major, 10)
        self.assertEqual(ver.minor, 20)
        self.assertEqual(ver.patch, 30)

    def test_semver_parse_invalid(self):
        invalid_values = ["", "1", "1.2", "1.2.3.4", "a.b.c", "v1.2.x"]
        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    SemVer.parse(value)

    def test_semver_to_tag_and_str(self):
        ver = SemVer(1, 2, 3)
        self.assertEqual(ver.to_tag(), "v1.2.3")
        self.assertEqual(ver.to_tag(with_prefix=False), "1.2.3")
        self.assertEqual(str(ver), "1.2.3")

    def test_is_semver_tag(self):
        cases = [
            ("1.2.3", True),
            ("v1.2.3", True),
            ("v0.0.0", True),
            ("1.2", False),
            ("foo", False),
            ("v1.2.x", False),
        ]
        for tag, expected in cases:
            with self.subTest(tag=tag):
                self.assertEqual(is_semver_tag(tag), expected)

    def test_extract_semver_from_tags_all(self):
        tags = ["v1.2.3", "1.0.0", "not-a-tag", "v2.0.1"]
        result = extract_semver_from_tags(tags)
        tag_strings = [t for (t, _v) in result]

        self.assertIn("v1.2.3", tag_strings)
        self.assertIn("1.0.0", tag_strings)
        self.assertIn("v2.0.1", tag_strings)
        self.assertNotIn("not-a-tag", tag_strings)

    def test_extract_semver_from_tags_filter_major(self):
        tags = ["v1.2.3", "v1.3.0", "v2.0.0", "v2.1.0"]
        result = extract_semver_from_tags(tags, major=1)
        tag_strings = {t for (t, _v) in result}
        self.assertEqual(tag_strings, {"v1.2.3", "v1.3.0"})

    def test_extract_semver_from_tags_filter_major_and_minor(self):
        tags = ["v1.2.3", "v1.2.4", "v1.3.0", "v2.2.0"]
        result = extract_semver_from_tags(tags, major=1, minor=2)
        tag_strings = {t for (t, _v) in result}
        self.assertEqual(tag_strings, {"v1.2.3", "v1.2.4"})

    def test_find_latest_version_simple(self):
        tags = ["v1.2.3", "v1.2.4", "v2.0.0"]
        latest = find_latest_version(tags)
        self.assertIsNotNone(latest)
        tag, ver = latest
        self.assertEqual(tag, "v2.0.0")
        self.assertEqual((ver.major, ver.minor, ver.patch), (2, 0, 0))

    def test_find_latest_version_filtered_major(self):
        tags = ["v1.2.3", "v1.4.0", "v2.0.0", "v2.1.0"]
        tag, ver = find_latest_version(tags, major=1)
        self.assertEqual(tag, "v1.4.0")
        self.assertEqual((ver.major, ver.minor, ver.patch), (1, 4, 0))

    def test_find_latest_version_filtered_major_minor(self):
        tags = ["v1.2.3", "v1.2.4", "v1.3.0"]
        tag, ver = find_latest_version(tags, major=1, minor=2)
        self.assertEqual(tag, "v1.2.4")
        self.assertEqual((ver.major, ver.minor, ver.patch), (1, 2, 4))

    def test_find_latest_version_no_match_returns_none(self):
        tags = ["not-semver", "also-bad"]
        latest = find_latest_version(tags)
        self.assertIsNone(latest)

    def test_bump_major(self):
        ver = SemVer(1, 2, 3)
        bumped = bump_major(ver)
        self.assertEqual((bumped.major, bumped.minor, bumped.patch), (2, 0, 0))

    def test_bump_minor(self):
        ver = SemVer(1, 2, 3)
        bumped = bump_minor(ver)
        self.assertEqual((bumped.major, bumped.minor, bumped.patch), (1, 3, 0))

    def test_bump_patch(self):
        ver = SemVer(1, 2, 3)
        bumped = bump_patch(ver)
        self.assertEqual((bumped.major, bumped.minor, bumped.patch), (1, 2, 4))


if __name__ == "__main__":
    unittest.main()
