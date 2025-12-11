#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import tempfile
import unittest

from pkgmgr.actions.mirror.io import (
    load_config_mirrors,
    read_mirrors_file,
)


class TestMirrorIO(unittest.TestCase):
    """
    Unit tests for pkgmgr.actions.mirror.io helpers.
    """

    # ------------------------------------------------------------------
    # load_config_mirrors
    # ------------------------------------------------------------------
    def test_load_config_mirrors_from_dict(self) -> None:
        repo = {
            "mirrors": {
                "origin": "ssh://git@example.com/account/repo.git",
                "backup": "ssh://git@backup/account/repo.git",
                "empty": "",
                "none": None,
            }
        }

        mirrors = load_config_mirrors(repo)

        self.assertEqual(
            mirrors,
            {
                "origin": "ssh://git@example.com/account/repo.git",
                "backup": "ssh://git@backup/account/repo.git",
            },
        )

    def test_load_config_mirrors_from_list(self) -> None:
        repo = {
            "mirrors": [
                {"name": "origin", "url": "ssh://git@example.com/account/repo.git"},
                {"name": "backup", "url": "ssh://git@backup/account/repo.git"},
                {"name": "", "url": "ssh://git@invalid/ignored.git"},
                {"name": "missing-url"},
                "not-a-dict",
            ]
        }

        mirrors = load_config_mirrors(repo)

        self.assertEqual(
            mirrors,
            {
                "origin": "ssh://git@example.com/account/repo.git",
                "backup": "ssh://git@backup/account/repo.git",
            },
        )

    def test_load_config_mirrors_empty_when_missing(self) -> None:
        repo = {}
        mirrors = load_config_mirrors(repo)
        self.assertEqual(mirrors, {})

    # ------------------------------------------------------------------
    # read_mirrors_file
    # ------------------------------------------------------------------
    def test_read_mirrors_file_with_named_and_url_only_entries(self) -> None:
        """
        Ensure that the MIRRORS file format is parsed correctly:

          - 'name url' → exact name
          - 'url'      → auto name derived from netloc (host[:port]),
                         with numeric suffix if duplicated.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            mirrors_path = os.path.join(tmpdir, "MIRRORS")
            content = "\n".join(
                [
                    "# comment",
                    "",
                    "origin ssh://git@example.com/account/repo.git",
                    "https://github.com/kevinveenbirkenbach/package-manager",
                    "https://github.com/kevinveenbirkenbach/another-repo",
                    "ssh://git@git.veen.world:2201/kevinveenbirkenbach/pkgmgr.git",
                ]
            )

            with open(mirrors_path, "w", encoding="utf-8") as fh:
                fh.write(content + "\n")

            mirrors = read_mirrors_file(tmpdir)

        # 'origin' is preserved as given
        self.assertIn("origin", mirrors)
        self.assertEqual(
            mirrors["origin"],
            "ssh://git@example.com/account/repo.git",
        )

        # Two GitHub URLs → auto names: github.com, github.com2
        github_urls = {
            mirrors.get("github.com"),
            mirrors.get("github.com2"),
        }
        self.assertIn(
            "https://github.com/kevinveenbirkenbach/package-manager",
            github_urls,
        )
        self.assertIn(
            "https://github.com/kevinveenbirkenbach/another-repo",
            github_urls,
        )

        # SSH-URL mit User-Teil → netloc ist "git@git.veen.world:2201"
        # → host = "git@git.veen.world"
        self.assertIn("git@git.veen.world", mirrors)
        self.assertEqual(
            mirrors["git@git.veen.world"],
            "ssh://git@git.veen.world:2201/kevinveenbirkenbach/pkgmgr.git",
        )

    def test_read_mirrors_file_missing_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mirrors = read_mirrors_file(tmpdir)  # no MIRRORS file
        self.assertEqual(mirrors, {})


if __name__ == "__main__":
    unittest.main()
