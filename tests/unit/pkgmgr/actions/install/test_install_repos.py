#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import unittest
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

from pkgmgr.actions.repository.install import install_repos


Repository = Dict[str, Any]


class TestInstallReposOrchestration(unittest.TestCase):
    def setUp(self) -> None:
        self.base_dir = "/fake/base"
        self.bin_dir = "/fake/bin"

        self.repo1: Repository = {
            "account": "kevinveenbirkenbach",
            "repository": "repo-one",
            "alias": "repo-one",
            "verified": {"gpg_keys": ["FAKEKEY"]},
        }
        self.repo2: Repository = {
            "account": "kevinveenbirkenbach",
            "repository": "repo-two",
            "alias": "repo-two",
            "verified": {"gpg_keys": ["FAKEKEY"]},
        }
        self.all_repos: List[Repository] = [self.repo1, self.repo2]

    @patch("pkgmgr.actions.repository.install.InstallationPipeline")
    @patch("pkgmgr.actions.repository.install.clone_repos")
    @patch("pkgmgr.actions.repository.install.get_repo_dir")
    @patch("pkgmgr.actions.repository.install.os.path.exists", return_value=True)
    @patch(
        "pkgmgr.actions.repository.install.verify_repository",
        return_value=(True, [], "hash", "key"),
    )
    def test_install_repos_runs_pipeline_for_each_repo(
        self,
        _mock_verify_repository: MagicMock,
        _mock_exists: MagicMock,
        mock_get_repo_dir: MagicMock,
        mock_clone_repos: MagicMock,
        mock_pipeline_cls: MagicMock,
    ) -> None:
        """
        install_repos() should construct a RepoContext for each repository and
        run the InstallationPipeline exactly once per selected repo when the
        repo directory exists and verification passes.
        """
        mock_get_repo_dir.side_effect = [
            os.path.join(self.base_dir, "repo-one"),
            os.path.join(self.base_dir, "repo-two"),
        ]

        selected = [self.repo1, self.repo2]

        install_repos(
            selected_repos=selected,
            repositories_base_dir=self.base_dir,
            bin_dir=self.bin_dir,
            all_repos=self.all_repos,
            no_verification=False,
            preview=False,
            quiet=False,
            clone_mode="ssh",
            update_dependencies=False,
        )

        # clone_repos must not be called because directories "exist"
        mock_clone_repos.assert_not_called()

        # A pipeline is constructed once, then run() is invoked once per repo
        self.assertEqual(mock_pipeline_cls.call_count, 1)
        pipeline_instance = mock_pipeline_cls.return_value
        self.assertEqual(pipeline_instance.run.call_count, len(selected))

    @patch("pkgmgr.actions.repository.install.InstallationPipeline")
    @patch("pkgmgr.actions.repository.install.clone_repos")
    @patch("pkgmgr.actions.repository.install.get_repo_dir")
    @patch("pkgmgr.actions.repository.install.os.path.exists", return_value=True)
    @patch(
        "pkgmgr.actions.repository.install.verify_repository",
        return_value=(False, ["invalid signature"], None, None),
    )
    @patch("builtins.input", return_value="n")
    def test_install_repos_skips_on_failed_verification(
        self,
        _mock_input: MagicMock,
        _mock_verify_repository: MagicMock,
        _mock_exists: MagicMock,
        mock_get_repo_dir: MagicMock,
        mock_clone_repos: MagicMock,
        mock_pipeline_cls: MagicMock,
    ) -> None:
        """
        When verification fails and the user does NOT confirm installation,
        the InstallationPipeline must not be run for that repository.
        """
        mock_get_repo_dir.return_value = os.path.join(self.base_dir, "repo-one")

        selected = [self.repo1]

        install_repos(
            selected_repos=selected,
            repositories_base_dir=self.base_dir,
            bin_dir=self.bin_dir,
            all_repos=self.all_repos,
            no_verification=False,
            preview=False,
            quiet=False,
            clone_mode="ssh",
            update_dependencies=False,
        )

        # clone_repos must not be called because directory "exists"
        mock_clone_repos.assert_not_called()

        # Pipeline is constructed, but run() must not be called
        mock_pipeline_cls.assert_called_once()
        pipeline_instance = mock_pipeline_cls.return_value
        pipeline_instance.run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
