#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CLI integration tests for `pkgmgr mirror`.

These tests validate:
- CLI argument parsing
- command dispatch
- command orchestration

All side effects (git, network, remote provisioning, filesystem writes)
are patched to keep tests deterministic and CI-safe.
"""

from __future__ import annotations

import io
import os
import runpy
import sys
import unittest
from contextlib import ExitStack, redirect_stderr, redirect_stdout
from typing import Dict, List, Optional
from unittest.mock import MagicMock, PropertyMock, patch


class TestIntegrationMirrorCommands(unittest.TestCase):
    """
    Integration tests for `pkgmgr mirror` commands.
    """

    def _run_pkgmgr(self, args: List[str], extra_env: Optional[Dict[str, str]] = None) -> str:
        """
        Execute pkgmgr with the given arguments and return captured output.

        - Treat SystemExit(0) or SystemExit(None) as success.
        - Any other exit code is considered a test failure.
        - Mirror commands are patched to avoid network/destructive operations.
        """
        original_argv = list(sys.argv)
        original_env = dict(os.environ)
        buffer = io.StringIO()
        cmd_repr = "pkgmgr " + " ".join(args)

        # Shared dummy context used by multiple mirror commands
        dummy_ctx = MagicMock()
        dummy_ctx.identifier = "dummy-repo"
        dummy_ctx.repo_dir = "/tmp/dummy-repo"
        dummy_ctx.config_mirrors = {"origin": "git@github.com:alice/repo.git"}
        dummy_ctx.file_mirrors = {"backup": "ssh://git@git.example:2201/alice/repo.git"}
        type(dummy_ctx).resolved_mirrors = PropertyMock(
            return_value={
                "origin": "git@github.com:alice/repo.git",
                "backup": "ssh://git@git.example:2201/alice/repo.git",
            }
        )

        # Helper: patch with create=True so missing modules/symbols don't explode
        def _p(target: str, **kwargs):
            return patch(target, create=True, **kwargs)

        # Fake result for remote provisioning (preview-safe)
        def _fake_ensure_remote_repo(spec, provider_hint=None, options=None):
            # Safety: E2E should only ever call this in preview mode
            if options is not None and getattr(options, "preview", False) is not True:
                raise AssertionError(f"{cmd_repr} attempted ensure_remote_repo without preview=True in E2E.")
            r = MagicMock()
            r.status = "preview"
            r.message = "Preview mode (E2E patched): no remote provisioning performed."
            r.url = None
            return r

        try:
            sys.argv = ["pkgmgr"] + list(args)
            if extra_env:
                os.environ.update(extra_env)

            with ExitStack() as stack:
                # build_context is imported directly in these modules:
                stack.enter_context(_p("pkgmgr.actions.mirror.list_cmd.build_context", return_value=dummy_ctx))
                stack.enter_context(_p("pkgmgr.actions.mirror.diff_cmd.build_context", return_value=dummy_ctx))
                stack.enter_context(_p("pkgmgr.actions.mirror.merge_cmd.build_context", return_value=dummy_ctx))
                stack.enter_context(_p("pkgmgr.actions.mirror.setup_cmd.build_context", return_value=dummy_ctx))
                stack.enter_context(_p("pkgmgr.actions.mirror.remote_provision.build_context", return_value=dummy_ctx))
                stack.enter_context(_p("pkgmgr.actions.mirror.check_cmd.build_context", return_value=dummy_ctx))

                # setup_cmd imports ensure_origin_remote and probe_mirror directly:
                stack.enter_context(_p("pkgmgr.actions.mirror.setup_cmd.ensure_origin_remote", return_value=None))
                stack.enter_context(_p("pkgmgr.actions.mirror.setup_cmd.probe_mirror", return_value=(True, "")))

                # check_cmd likely imports probe_mirror directly too (make it deterministic)
                stack.enter_context(_p("pkgmgr.actions.mirror.check_cmd.probe_mirror", return_value=(True, "")))

                # remote provisioning: remote_provision imports ensure_remote_repo directly from core:
                stack.enter_context(
                    _p(
                        "pkgmgr.actions.mirror.remote_provision.ensure_remote_repo",
                        side_effect=_fake_ensure_remote_repo,
                    )
                )

                # Extra safety: if anything calls remote_check.run_git directly, make it inert
                stack.enter_context(_p("pkgmgr.actions.mirror.remote_check.run_git", return_value="dummy"))

                with redirect_stdout(buffer), redirect_stderr(buffer):
                    try:
                        runpy.run_module("pkgmgr", run_name="__main__")
                    except SystemExit as exc:
                        code = exc.code if isinstance(exc.code, int) else None
                        if code not in (0, None):
                            raise AssertionError(
                                "%r failed with exit code %r.\n\nOutput:\n%s"
                                % (cmd_repr, exc.code, buffer.getvalue())
                            )


            return buffer.getvalue()

        finally:
            sys.argv = original_argv
            os.environ.clear()
            os.environ.update(original_env)

    # ------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------

    def test_mirror_help(self) -> None:
        output = self._run_pkgmgr(["mirror", "--help"])
        self.assertIn("usage:", output.lower())
        self.assertIn("mirror", output.lower())

    def test_mirror_list_preview_all(self) -> None:
        output = self._run_pkgmgr(["mirror", "list", "--preview", "--all"])
        self.assertTrue(output.strip(), "Expected output from mirror list")

    def test_mirror_diff_preview_all(self) -> None:
        output = self._run_pkgmgr(["mirror", "diff", "--preview", "--all"])
        self.assertTrue(output.strip(), "Expected output from mirror diff")

    def test_mirror_merge_config_to_file_preview_all(self) -> None:
        output = self._run_pkgmgr(["mirror", "merge", "config", "file", "--preview", "--all"])
        self.assertTrue(output.strip(), "Expected output from mirror merge (config -> file)")

    def test_mirror_setup_preview_all(self) -> None:
        output = self._run_pkgmgr(["mirror", "setup", "--preview", "--all"])
        self.assertTrue(output.strip(), "Expected output from mirror setup")

    def test_mirror_check_preview_all(self) -> None:
        output = self._run_pkgmgr(["mirror", "check", "--preview", "--all"])
        self.assertTrue(output.strip(), "Expected output from mirror check")

    def test_mirror_provision_preview_all(self) -> None:
        output = self._run_pkgmgr(["mirror", "provision", "--preview", "--all"])
        self.assertTrue(output.strip(), "Expected output from mirror provision (preview)")


if __name__ == "__main__":
    unittest.main()
