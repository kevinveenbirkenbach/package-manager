from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from pkgmgr.actions.install.installers.nix.installer import NixFlakeInstaller
from ._fakes import FakeRunResult


class DummyCtx:
    def __init__(self, identifier: str = "x", repo_dir: str = "/repo", quiet: bool = True, force_update: bool = False):
        self.identifier = identifier
        self.repo_dir = repo_dir
        self.quiet = quiet
        self.force_update = force_update


class TestNixFlakeInstallerCore(unittest.TestCase):
    def test_install_only_success_returns(self) -> None:
        ins = NixFlakeInstaller()
        ins.supports = MagicMock(return_value=True)

        ins._retry = MagicMock()
        ins._retry.run_with_retry.return_value = FakeRunResult(0, "", "")
        ins._conflicts = MagicMock()
        ins._profile = MagicMock()
        ins._runner = MagicMock()

        ctx = DummyCtx(identifier="lib", repo_dir="/repo", quiet=True)
        ins.run(ctx)
        ins._retry.run_with_retry.assert_called()

    def test_conflict_resolver_success_short_circuits(self) -> None:
        ins = NixFlakeInstaller()
        ins.supports = MagicMock(return_value=True)

        ins._retry = MagicMock()
        ins._retry.run_with_retry.return_value = FakeRunResult(1, "out", "err")
        ins._conflicts = MagicMock()
        ins._conflicts.resolve.return_value = True
        ins._profile = MagicMock()
        ins._runner = MagicMock()

        ctx = DummyCtx(identifier="lib", repo_dir="/repo", quiet=True)
        ins.run(ctx)
        ins._conflicts.resolve.assert_called()

    def test_mandatory_failure_raises_systemexit(self) -> None:
        ins = NixFlakeInstaller()
        ins.supports = MagicMock(return_value=True)

        ins._retry = MagicMock()
        ins._retry.run_with_retry.return_value = FakeRunResult(2, "", "no")
        ins._conflicts = MagicMock()
        ins._conflicts.resolve.return_value = False
        ins._profile = MagicMock()
        ins._profile.find_installed_indices_for_output.return_value = []
        ins._runner = MagicMock()
        ins._runner.run.return_value = FakeRunResult(2, "", "")

        ctx = DummyCtx(identifier="lib", repo_dir="/repo", quiet=True)
        with self.assertRaises(SystemExit) as cm:
            ins.run(ctx)
        self.assertEqual(cm.exception.code, 2)

    def test_optional_failure_does_not_raise(self) -> None:
        ins = NixFlakeInstaller()
        ins.supports = MagicMock(return_value=True)

        results = [
            FakeRunResult(0, "", ""),
            FakeRunResult(2, "", ""),
        ]

        def run_with_retry(ctx, runner, cmd):
            return results.pop(0)

        ins._retry = MagicMock()
        ins._retry.run_with_retry.side_effect = run_with_retry
        ins._conflicts = MagicMock()
        ins._conflicts.resolve.return_value = False
        ins._profile = MagicMock()
        ins._profile.find_installed_indices_for_output.return_value = []
        ins._runner = MagicMock()
        ins._runner.run.return_value = FakeRunResult(2, "", "")

        ctx = DummyCtx(identifier="pkgmgr", repo_dir="/repo", quiet=True)
        ins.run(ctx)  # must not raise
