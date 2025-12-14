#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import tempfile
import unittest

from pkgmgr.actions.mirror.io import load_config_mirrors, read_mirrors_file, write_mirrors_file


class TestMirrorIO(unittest.TestCase):
    """
    Unit tests for pkgmgr.actions.mirror.io helpers.
    """

    def test_load_config_mirrors_from_dict_filters_empty(self) -> None:
        repo = {
            "mirrors": {
                "origin": "ssh://git@example.com/account/repo.git",
                "backup": "",
                "invalid": None,
            }
        }

        mirrors = load_config_mirrors(repo)
        self.assertEqual(mirrors, {"origin": "ssh://git@example.com/account/repo.git"})

    def test_load_config_mirrors_from_list_filters_invalid_entries(self) -> None:
        repo = {
            "mirrors": [
                {"name": "origin", "url": "ssh://git@example.com/account/repo.git"},
                {"name": "backup", "url": ""},
                {"name": "", "url": "ssh://git@example.com/empty-name.git"},
                {"url": "ssh://git@example.com/missing-name.git"},
            ]
        }

        mirrors = load_config_mirrors(repo)
        self.assertEqual(mirrors, {"origin": "ssh://git@example.com/account/repo.git"})

    def test_load_config_mirrors_empty_when_missing(self) -> None:
        self.assertEqual(load_config_mirrors({}), {})

    def test_read_mirrors_file_parses_named_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            p = os.path.join(tmpdir, "MIRRORS")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("origin ssh://git@example.com/account/repo.git\n")

            mirrors = read_mirrors_file(tmpdir)

        self.assertEqual(mirrors, {"origin": "ssh://git@example.com/account/repo.git"})

    def test_read_mirrors_file_url_only_uses_netloc_basename_and_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            p = os.path.join(tmpdir, "MIRRORS")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(
                    "\n".join(
                        [
                            "https://github.com/alice/repo1",
                            "https://github.com/alice/repo2",
                            "ssh://git@git.veen.world:2201/alice/repo3.git",
                        ]
                    )
                    + "\n"
                )

            mirrors = read_mirrors_file(tmpdir)

        self.assertIn("github.com", mirrors)
        self.assertIn("github.com2", mirrors)
        self.assertEqual(mirrors["github.com"], "https://github.com/alice/repo1")
        self.assertEqual(mirrors["github.com2"], "https://github.com/alice/repo2")

        self.assertIn("git@git.veen.world", mirrors)
        self.assertEqual(mirrors["git@git.veen.world"], "ssh://git@git.veen.world:2201/alice/repo3.git")

    def test_read_mirrors_file_missing_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            self.assertEqual(read_mirrors_file(tmpdir), {})

    def test_write_mirrors_file_writes_sorted_lines(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mirrors = {
                "b": "ssh://b.example/repo.git",
                "a": "ssh://a.example/repo.git",
            }
            write_mirrors_file(tmpdir, mirrors, preview=False)

            p = os.path.join(tmpdir, "MIRRORS")
            self.assertTrue(os.path.exists(p))

            with open(p, "r", encoding="utf-8") as fh:
                content = fh.read()

        self.assertEqual(content, "a ssh://a.example/repo.git\nb ssh://b.example/repo.git\n")

    def test_write_mirrors_file_preview_does_not_create_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mirrors = {"a": "ssh://a.example/repo.git"}
            write_mirrors_file(tmpdir, mirrors, preview=True)

            p = os.path.join(tmpdir, "MIRRORS")
            self.assertFalse(os.path.exists(p))


if __name__ == "__main__":
    unittest.main()
