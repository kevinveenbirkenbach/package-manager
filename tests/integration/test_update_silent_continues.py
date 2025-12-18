#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.update.manager import UpdateManager


class TestUpdateSilentContinues(unittest.TestCase):
    def test_update_continues_on_failures_and_silent_controls_exit_code(self) -> None:
        """
        Integration test for UpdateManager:
          - pull failure on repo A should not stop repo B/C
          - install failure on repo B should not stop repo C
          - without silent -> SystemExit(1) at end if any failures
          - with silent -> no SystemExit even if there are failures
        """

        repos = [
            {"provider": "github", "account": "example", "repository": "repo-a"},
            {"provider": "github", "account": "example", "repository": "repo-b"},
            {"provider": "github", "account": "example", "repository": "repo-c"},
        ]

        # We patch the internal calls used by UpdateManager:
        # - pull_with_verification is called once per repo
        # - install_repos is called once per repo that successfully pulled
        #
        # We simulate:
        #   repo-a: pull fails
        #   repo-b: pull ok, install fails
        #   repo-c: pull ok, install ok
        pull_calls = []
        install_calls = []

        def pull_side_effect(selected_repos, *_args, **_kwargs):
            # selected_repos is a list with exactly one repo in our implementation.
            repo = selected_repos[0]
            pull_calls.append(repo["repository"])
            if repo["repository"] == "repo-a":
                raise SystemExit(2)
            return None

        def install_side_effect(selected_repos, *_args, **kwargs):
            repo = selected_repos[0]
            install_calls.append(
                (repo["repository"], kwargs.get("silent"), kwargs.get("emit_summary"))
            )
            if repo["repository"] == "repo-b":
                raise SystemExit(3)
            return None

        # Patch at the exact import locations used inside UpdateManager.run()
        with (
            patch(
                "pkgmgr.actions.repository.pull.pull_with_verification",
                side_effect=pull_side_effect,
            ),
            patch(
                "pkgmgr.actions.install.install_repos", side_effect=install_side_effect
            ),
        ):
            # 1) silent=True: should NOT raise (even though failures happened)
            UpdateManager().run(
                selected_repos=repos,
                repositories_base_dir="/tmp/repos",
                bin_dir="/tmp/bin",
                all_repos=repos,
                no_verification=True,
                system_update=False,
                preview=True,
                quiet=True,
                update_dependencies=False,
                clone_mode="shallow",
                silent=True,
                force_update=True,
            )

            # Ensure it tried all pulls, and installs happened for B and C only.
            self.assertEqual(pull_calls, ["repo-a", "repo-b", "repo-c"])
            self.assertEqual(
                [r for r, _silent, _emit in install_calls], ["repo-b", "repo-c"]
            )

            # Ensure UpdateManager suppressed install summary spam by passing emit_summary=False.
            for _repo_name, _silent, emit_summary in install_calls:
                self.assertFalse(emit_summary)

            # Reset tracking for the non-silent run
            pull_calls.clear()
            install_calls.clear()

            # 2) silent=False: should raise SystemExit(1) at end due to failures
            with self.assertRaises(SystemExit) as cm:
                UpdateManager().run(
                    selected_repos=repos,
                    repositories_base_dir="/tmp/repos",
                    bin_dir="/tmp/bin",
                    all_repos=repos,
                    no_verification=True,
                    system_update=False,
                    preview=True,
                    quiet=True,
                    update_dependencies=False,
                    clone_mode="shallow",
                    silent=False,
                    force_update=True,
                )
            self.assertEqual(cm.exception.code, 1)

            # Still must have processed all repos (continue-on-failure behavior).
            self.assertEqual(pull_calls, ["repo-a", "repo-b", "repo-c"])
            self.assertEqual(
                [r for r, _silent, _emit in install_calls], ["repo-b", "repo-c"]
            )


if __name__ == "__main__":
    unittest.main()
