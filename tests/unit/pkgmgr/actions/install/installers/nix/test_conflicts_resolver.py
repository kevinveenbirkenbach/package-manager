from __future__ import annotations

import unittest

from pkgmgr.actions.install.installers.nix.conflicts import NixConflictResolver
from ._fakes import FakeRunResult, FakeRunner, FakeRetry


class DummyCtx:
    quiet = True


class TestNixConflictResolver(unittest.TestCase):
    def test_resolve_removes_tokens_and_retries_success(self) -> None:
        ctx = DummyCtx()
        install_cmd = "nix profile install /repo#default"

        stderr = '''
        error: An existing package already provides the following file:
          /nix/store/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-pkgmgr/bin/pkgmgr
        '''

        runner = FakeRunner(mapping={
            "nix profile remove pkgmgr": FakeRunResult(0, "", ""),
        })
        retry = FakeRetry(results=[FakeRunResult(0, "", "")])

        class FakeProfile:
            def find_remove_tokens_for_store_prefixes(self, ctx, runner, prefixes):
                return []
            def find_remove_tokens_for_output(self, ctx, runner, output):
                return ["pkgmgr"]

        resolver = NixConflictResolver(runner=runner, retry=retry, profile=FakeProfile())
        ok = resolver.resolve(ctx, install_cmd, stdout="", stderr=stderr, output="pkgmgr", max_rounds=2)
        self.assertTrue(ok)
        self.assertIn("nix profile remove pkgmgr", [c[1] for c in runner.calls])

    def test_resolve_uses_textual_remove_tokens_last_resort(self) -> None:
        ctx = DummyCtx()
        install_cmd = "nix profile install /repo#default"

        stderr = "hint: try:\n  nix profile remove 'pkgmgr-1'\n"
        runner = FakeRunner(mapping={
            "nix profile remove pkgmgr-1": FakeRunResult(0, "", ""),
        })
        retry = FakeRetry(results=[FakeRunResult(0, "", "")])

        class FakeProfile:
            def find_remove_tokens_for_store_prefixes(self, ctx, runner, prefixes):
                return []
            def find_remove_tokens_for_output(self, ctx, runner, output):
                return []

        resolver = NixConflictResolver(runner=runner, retry=retry, profile=FakeProfile())
        ok = resolver.resolve(ctx, install_cmd, stdout="", stderr=stderr, output="pkgmgr", max_rounds=2)
        self.assertTrue(ok)
        self.assertIn("nix profile remove pkgmgr-1", [c[1] for c in runner.calls])
