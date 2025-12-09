#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pkgmgr.core.repository.selected import get_selected_repos


def _repo(
    provider: str,
    account: str,
    repository: str,
    ignore: bool | None = None,
    directory: str | None = None,
):
    repo = {
        "provider": provider,
        "account": account,
        "repository": repository,
    }
    if ignore is not None:
        repo["ignore"] = ignore
    if directory is not None:
        repo["directory"] = directory
    return repo


class TestGetSelectedRepos(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_ignored = _repo(
            "github.com",
            "user",
            "ignored-repo",
            ignore=True,
            directory="/repos/github.com/user/ignored-repo",
        )
        self.repo_visible = _repo(
            "github.com",
            "user",
            "visible-repo",
            ignore=False,
            directory="/repos/github.com/user/visible-repo",
        )
        self.all_repos = [self.repo_ignored, self.repo_visible]

    # ------------------------------------------------------------------
    # 1) Explizite Identifier – ignorierte Repos dürfen ausgewählt werden
    # ------------------------------------------------------------------
    def test_identifiers_bypass_ignore_filter(self) -> None:
        args = SimpleNamespace(
            identifiers=["ignored-repo"],  # matches by repository name
            all=False,
            category=[],
            string="",
            tag=[],
            include_ignored=False,  # should be ignored for explicit identifiers
        )

        selected = get_selected_repos(args, self.all_repos)

        self.assertEqual(len(selected), 1)
        self.assertIs(selected[0], self.repo_ignored)

    # ------------------------------------------------------------------
    # 2) Filter-only Modus – ignorierte Repos werden rausgefiltert
    # ------------------------------------------------------------------
    def test_filter_mode_excludes_ignored_by_default(self) -> None:
        # string-Filter, der beide Repos matchen würde
        args = SimpleNamespace(
            identifiers=[],
            all=False,
            category=[],
            string="repo",  # substring in beiden Namen
            tag=[],
            include_ignored=False,
        )

        selected = get_selected_repos(args, self.all_repos)

        self.assertEqual(len(selected), 1)
        self.assertIs(selected[0], self.repo_visible)

    def test_filter_mode_can_include_ignored_when_flag_set(self) -> None:
        args = SimpleNamespace(
            identifiers=[],
            all=False,
            category=[],
            string="repo",
            tag=[],
            include_ignored=True,
        )

        selected = get_selected_repos(args, self.all_repos)

        # Beide Repos sollten erscheinen, weil include_ignored=True
        self.assertEqual({r["repository"] for r in selected}, {"ignored-repo", "visible-repo"})

    # ------------------------------------------------------------------
    # 3) --all Modus – ignorierte Repos werden per Default entfernt
    # ------------------------------------------------------------------
    def test_all_mode_excludes_ignored_by_default(self) -> None:
        args = SimpleNamespace(
            identifiers=[],
            all=True,
            category=[],
            string="",
            tag=[],
            include_ignored=False,
        )

        selected = get_selected_repos(args, self.all_repos)

        self.assertEqual(len(selected), 1)
        self.assertIs(selected[0], self.repo_visible)

    def test_all_mode_can_include_ignored_when_flag_set(self) -> None:
        args = SimpleNamespace(
            identifiers=[],
            all=True,
            category=[],
            string="",
            tag=[],
            include_ignored=True,
        )

        selected = get_selected_repos(args, self.all_repos)

        self.assertEqual(len(selected), 2)
        self.assertCountEqual(
            [r["repository"] for r in selected],
            ["ignored-repo", "visible-repo"],
        )

    # ------------------------------------------------------------------
    # 4) CWD-Modus – Repo anhand des aktuellen Verzeichnisses auswählen
    # ------------------------------------------------------------------
    def test_cwd_selection_excludes_ignored_by_default(self) -> None:
        # Wir lassen CWD auf das Verzeichnis des ignorierten Repos zeigen.
        cwd = os.path.abspath(self.repo_ignored["directory"])

        args = SimpleNamespace(
            identifiers=[],
            all=False,
            category=[],
            string="",
            tag=[],
            include_ignored=False,
        )

        with patch("os.getcwd", return_value=cwd):
            selected = get_selected_repos(args, self.all_repos)

        # Da das einzige Repo für dieses Verzeichnis ignoriert ist,
        # sollte die Auswahl leer sein.
        self.assertEqual(selected, [])

    def test_cwd_selection_can_include_ignored_when_flag_set(self) -> None:
        cwd = os.path.abspath(self.repo_ignored["directory"])

        args = SimpleNamespace(
            identifiers=[],
            all=False,
            category=[],
            string="",
            tag=[],
            include_ignored=True,
        )

        with patch("os.getcwd", return_value=cwd):
            selected = get_selected_repos(args, self.all_repos)

        self.assertEqual(len(selected), 1)
        self.assertIs(selected[0], self.repo_ignored)


if __name__ == "__main__":
    unittest.main()
