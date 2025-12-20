#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration test for mirror probing + provisioning after refactor.

We test the CLI entrypoint `handle_mirror_command()` directly to avoid
depending on repo-selection / config parsing for `--all`.

Covers:
- setup_cmd uses probe_remote_reachable_detail()
- check prints [OK]/[WARN] and 'reason:' lines for failures
- provision triggers ensure_remote_repo (preview-safe) for each git mirror
"""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, PropertyMock, patch

from pkgmgr.cli.commands.mirror import handle_mirror_command


class TestIntegrationMirrorProbeDetailAndProvision(unittest.TestCase):
    def _make_ctx(
        self, *, repositories_base_dir: str, all_repositories: list[dict]
    ) -> MagicMock:
        ctx = MagicMock()
        ctx.repositories_base_dir = repositories_base_dir
        ctx.all_repositories = all_repositories
        # mirror merge may look at this; keep it present for safety
        ctx.user_config_path = str(Path(repositories_base_dir) / "user.yml")
        return ctx

    def _make_dummy_repo_ctx(self, *, repo_dir: str) -> MagicMock:
        """
        This is the RepoMirrorContext-like object returned by build_context().
        """
        dummy = MagicMock()
        dummy.identifier = "dummy-repo"
        dummy.repo_dir = repo_dir
        dummy.config_mirrors = {"origin": "git@github.com:alice/repo.git"}
        dummy.file_mirrors = {"backup": "ssh://git@git.example:2201/alice/repo.git"}
        type(dummy).resolved_mirrors = PropertyMock(
            return_value={
                "origin": "git@github.com:alice/repo.git",
                "backup": "ssh://git@git.example:2201/alice/repo.git",
            }
        )
        return dummy

    def _run_handle(
        self,
        *,
        subcommand: str,
        preview: bool,
        selected: list[dict],
        dummy_repo_dir: str,
        probe_detail_side_effect,
    ) -> str:
        """
        Run handle_mirror_command() with patched side effects and capture output.
        """
        args = SimpleNamespace(subcommand=subcommand, preview=preview)

        # Fake ensure_remote_repo result (preview safe)
        def _fake_ensure_remote_repo(spec, provider_hint=None, options=None):
            if options is not None and getattr(options, "preview", False) is not True:
                raise AssertionError(
                    "ensure_remote_repo called without preview=True (should never happen in tests)."
                )
            r = MagicMock()
            r.status = "preview"
            r.message = "Preview mode: no remote provisioning performed."
            r.url = None
            return r

        buf = io.StringIO()
        ctx = self._make_ctx(
            repositories_base_dir=str(Path(dummy_repo_dir).parent),
            all_repositories=selected,
        )
        dummy_repo_ctx = self._make_dummy_repo_ctx(repo_dir=dummy_repo_dir)

        with (
            patch(
                "pkgmgr.actions.mirror.setup_cmd.build_context",
                return_value=dummy_repo_ctx,
            ),
            patch(
                "pkgmgr.actions.mirror.setup_cmd.ensure_origin_remote",
                return_value=None,
            ),
            patch(
                "pkgmgr.actions.mirror.git_remote.ensure_origin_remote",
                return_value=None,
            ),
            patch(
                "pkgmgr.actions.mirror.setup_cmd.probe_remote_reachable_detail",
                side_effect=probe_detail_side_effect,
            ),
            patch(
                "pkgmgr.actions.mirror.remote_provision.ensure_remote_repo",
                side_effect=_fake_ensure_remote_repo,
            ),
            redirect_stdout(buf),
            redirect_stderr(buf),
        ):
            handle_mirror_command(ctx, args, selected)

        return buf.getvalue()

    def test_mirror_check_preview_prints_warn_reason(self) -> None:
        """
        'mirror check --preview' should:
        - probe both git mirrors
        - print [OK] for origin
        - print [WARN] for backup + reason line
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo_dir = tmp_path / "dummy-repo"
            repo_dir.mkdir(parents=True, exist_ok=True)

            selected = [
                {"provider": "github.com", "account": "alice", "repository": "repo"}
            ]

            def probe_side_effect(url: str, cwd: str = "."):
                if "github.com" in url:
                    # show "empty repo reachable" note; setup_cmd prints [OK] and does not print reason for ok
                    return (
                        True,
                        "remote reachable, but no refs found yet (empty repository)",
                    )
                return False, "(exit 128) fatal: Could not read from remote repository."

            out = self._run_handle(
                subcommand="check",
                preview=True,
                selected=selected,
                dummy_repo_dir=str(repo_dir),
                probe_detail_side_effect=probe_side_effect,
            )

            self.assertIn("[MIRROR SETUP:REMOTE]", out)

            # origin OK (even with a note returned; still OK)
            self.assertIn("[OK] origin: git@github.com:alice/repo.git", out)

            # backup WARN prints reason line
            self.assertIn(
                "[WARN] backup: ssh://git@git.example:2201/alice/repo.git", out
            )
            self.assertIn("reason:", out)
            self.assertIn("Could not read from remote repository", out)

    def test_mirror_provision_preview_provisions_each_git_mirror(self) -> None:
        """
        'mirror provision --preview' should:
        - print provisioning lines for each git mirror
        - still probe and print [OK]/[WARN]
        - call ensure_remote_repo only in preview mode (enforced by fake)
        """
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            repo_dir = tmp_path / "dummy-repo"
            repo_dir.mkdir(parents=True, exist_ok=True)

            selected = [
                {
                    "provider": "github.com",
                    "account": "alice",
                    "repository": "repo",
                    "private": True,
                    "description": "desc",
                }
            ]

            def probe_side_effect(url: str, cwd: str = "."):
                if "github.com" in url:
                    return True, ""
                return False, "(exit 128) fatal: Could not read from remote repository."

            out = self._run_handle(
                subcommand="provision",
                preview=True,
                selected=selected,
                dummy_repo_dir=str(repo_dir),
                probe_detail_side_effect=probe_side_effect,
            )

            # provisioning should attempt BOTH mirrors
            self.assertIn(
                "[REMOTE ENSURE] ensuring mirror 'origin': git@github.com:alice/repo.git",
                out,
            )
            self.assertIn(
                "[REMOTE ENSURE] ensuring mirror 'backup': ssh://git@git.example:2201/alice/repo.git",
                out,
            )

            # patched ensure_remote_repo prints PREVIEW status via remote_provision
            self.assertIn("[REMOTE ENSURE]", out)
            self.assertIn("PREVIEW", out.upper())

            # probes after provisioning
            self.assertIn("[OK] origin: git@github.com:alice/repo.git", out)
            self.assertIn(
                "[WARN] backup: ssh://git@git.example:2201/alice/repo.git", out
            )


if __name__ == "__main__":
    unittest.main()
