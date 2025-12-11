#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest

from pkgmgr.actions.mirror.git_remote import (
    build_default_ssh_url,
    determine_primary_remote_url,
)
from pkgmgr.actions.mirror.types import MirrorMap, Repository


class TestMirrorGitRemote(unittest.TestCase):
    """
    Unit tests for SSH URL and primary remote selection logic.
    """

    def test_build_default_ssh_url_without_port(self) -> None:
        repo: Repository = {
            "provider": "github.com",
            "account": "kevinveenbirkenbach",
            "repository": "package-manager",
        }

        url = build_default_ssh_url(repo)
        self.assertEqual(
            url,
            "git@github.com:kevinveenbirkenbach/package-manager.git",
        )

    def test_build_default_ssh_url_with_port(self) -> None:
        repo: Repository = {
            "provider": "code.cymais.cloud",
            "account": "kevinveenbirkenbach",
            "repository": "pkgmgr",
            "port": 2201,
        }

        url = build_default_ssh_url(repo)
        self.assertEqual(
            url,
            "ssh://git@code.cymais.cloud:2201/kevinveenbirkenbach/pkgmgr.git",
        )

    def test_build_default_ssh_url_missing_fields_returns_none(self) -> None:
        repo: Repository = {
            "provider": "github.com",
            "account": "kevinveenbirkenbach",
            # "repository" fehlt absichtlich
        }

        url = build_default_ssh_url(repo)
        self.assertIsNone(url)

    def test_determine_primary_remote_url_prefers_origin_in_resolved_mirrors(
        self,
    ) -> None:
        repo: Repository = {
            "provider": "github.com",
            "account": "kevinveenbirkenbach",
            "repository": "package-manager",
        }
        mirrors: MirrorMap = {
            "origin": "git@github.com:kevinveenbirkenbach/package-manager.git",
            "backup": "ssh://git@git.veen.world:2201/kevinveenbirkenbach/pkgmgr.git",
        }

        url = determine_primary_remote_url(repo, mirrors)
        self.assertEqual(
            url,
            "git@github.com:kevinveenbirkenbach/package-manager.git",
        )

    def test_determine_primary_remote_url_uses_any_mirror_if_no_origin(self) -> None:
        repo: Repository = {
            "provider": "github.com",
            "account": "kevinveenbirkenbach",
            "repository": "package-manager",
        }
        mirrors: MirrorMap = {
            "backup": "ssh://git@git.veen.world:2201/kevinveenbirkenbach/pkgmgr.git",
            "mirror2": "ssh://git@code.cymais.cloud:2201/kevinveenbirkenbach/pkgmgr.git",
        }

        url = determine_primary_remote_url(repo, mirrors)
        # Alphabetisch sortiert: backup, mirror2 → backup gewinnt
        self.assertEqual(
            url,
            "ssh://git@git.veen.world:2201/kevinveenbirkenbach/pkgmgr.git",
        )

    def test_determine_primary_remote_url_falls_back_to_default_ssh(self) -> None:
        repo: Repository = {
            "provider": "github.com",
            "account": "kevinveenbirkenbach",
            "repository": "package-manager",
        }
        mirrors: MirrorMap = {}

        url = determine_primary_remote_url(repo, mirrors)
        self.assertEqual(
            url,
            "git@github.com:kevinveenbirkenbach/package-manager.git",
        )


if __name__ == "__main__":
    unittest.main()
