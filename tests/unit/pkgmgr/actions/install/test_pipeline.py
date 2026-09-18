from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from pkgmgr.actions.install.context import RepoContext
from pkgmgr.actions.install.installers.base import BaseInstaller
from pkgmgr.actions.install.layers import CliLayer
from pkgmgr.actions.install.pipeline import InstallationPipeline


class DummyInstaller(BaseInstaller):
    """
    Small fake installer with configurable layer, supports() result,
    and advertised capabilities.
    """

    def __init__(
        self,
        name: str,
        layer: str | None = None,
        supports_result: bool = True,
        capabilities: set[str] | None = None,
        fails: bool = False,
    ) -> None:
        self._name = name
        self.layer = layer  # type: ignore[assignment]
        self._supports_result = supports_result
        self._capabilities = capabilities or set()
        self._fails = fails
        self.ran = False

    def supports(self, ctx: RepoContext) -> bool:  # type: ignore[override]
        return self._supports_result

    def run(self, ctx: RepoContext) -> None:  # type: ignore[override]
        self.ran = True
        if self._fails:
            raise SystemExit(2)

    def discover_capabilities(self, ctx: RepoContext) -> set[str]:  # type: ignore[override]
        return set(self._capabilities)


def _minimal_context() -> RepoContext:
    repo = {
        "account": "kevinveenbirkenbach",
        "repository": "test-repo",
        "alias": "test-repo",
    }
    return RepoContext(
        repo=repo,
        identifier="test-repo",
        repo_dir="/tmp/test-repo",
        repositories_base_dir="/tmp",
        bin_dir="/usr/local/bin",
        all_repos=[repo],
        no_verification=False,
        preview=False,
        quiet=False,
        clone_mode="ssh",
        update_dependencies=False,
    )


class TestInstallationPipeline(unittest.TestCase):
    @patch("pkgmgr.actions.install.pipeline.create_ink")
    @patch("pkgmgr.actions.install.pipeline.resolve_command_for_repo")
    def test_create_ink_called_when_command_resolved(
        self,
        mock_resolve_command_for_repo: MagicMock,
        mock_create_ink: MagicMock,
    ) -> None:
        """
        If resolve_command_for_repo returns a command, InstallationPipeline
        must attach it to the repo and call create_ink().
        """
        mock_resolve_command_for_repo.return_value = "/usr/local/bin/test-repo"

        ctx = _minimal_context()
        installer = DummyInstaller("noop-installer", supports_result=False)
        pipeline = InstallationPipeline([installer])

        pipeline.run(ctx)

        self.assertTrue(mock_create_ink.called)
        self.assertEqual(
            ctx.repo.get("command"),
            "/usr/local/bin/test-repo",
        )

    @patch("pkgmgr.actions.install.pipeline.create_ink")
    @patch("pkgmgr.actions.install.pipeline.resolve_command_for_repo")
    def test_lower_priority_installers_are_skipped_if_cli_exists(
        self,
        mock_resolve_command_for_repo: MagicMock,
        mock_create_ink: MagicMock,
    ) -> None:
        """
        If the resolved command is provided by a higher-priority layer
        (e.g. OS_PACKAGES), a lower-priority installer (e.g. PYTHON)
        must be skipped.
        """
        mock_resolve_command_for_repo.return_value = "/usr/bin/test-repo"

        ctx = _minimal_context()
        python_installer = DummyInstaller(
            "python-installer",
            layer=CliLayer.PYTHON.value,
            supports_result=True,
        )
        pipeline = InstallationPipeline([python_installer])

        pipeline.run(ctx)

        self.assertFalse(
            python_installer.ran,
            "Python installer must not run when an OS_PACKAGES CLI already exists.",
        )
        self.assertEqual(ctx.repo.get("command"), "/usr/bin/test-repo")

    @patch("pkgmgr.actions.install.pipeline.create_ink")
    @patch("pkgmgr.actions.install.pipeline.resolve_command_for_repo")
    def test_only_one_installation_hook_runs(
        self,
        mock_resolve_command_for_repo: MagicMock,
        mock_create_ink: MagicMock,
    ) -> None:
        """A repository is installed once, by the first hook that supports it."""
        mock_resolve_command_for_repo.return_value = None  # no CLI initially

        ctx = _minimal_context()
        first = DummyInstaller(
            "first-installer",
            layer=CliLayer.PYTHON.value,
            supports_result=True,
            capabilities={"cli"},
        )
        second = DummyInstaller(
            "second-installer",
            layer=CliLayer.PYTHON.value,
            supports_result=True,
            capabilities={"cli"},  # same capability
        )

        pipeline = InstallationPipeline([first, second])
        pipeline.run(ctx)

        self.assertTrue(first.ran, "First installer should run.")
        self.assertFalse(
            second.ran,
            "A second installation hook must not run after the first one did.",
        )

    @patch("pkgmgr.actions.install.pipeline.create_ink")
    @patch("pkgmgr.actions.install.pipeline.resolve_command_for_repo")
    def test_a_differing_second_hook_is_not_run_either(
        self,
        mock_resolve_command_for_repo: MagicMock,
        mock_create_ink: MagicMock,
    ) -> None:
        """The rule is one hook, not one hook per capability."""
        mock_resolve_command_for_repo.return_value = None

        ctx = _minimal_context()
        first = DummyInstaller(
            "python-installer",
            layer=CliLayer.PYTHON.value,
            supports_result=True,
            capabilities={"python-runtime"},
        )
        second = DummyInstaller(
            "makefile-installer",
            layer=CliLayer.MAKEFILE.value,
            supports_result=True,
            capabilities={"make-install"},
        )

        pipeline = InstallationPipeline([first, second])
        pipeline.run(ctx)

        self.assertTrue(first.ran, "The first supported hook should run.")
        self.assertFalse(
            second.ran,
            "A hook advertising a different capability must not run either: "
            "the project is already installed.",
        )

    @patch("pkgmgr.actions.install.pipeline.create_ink")
    @patch("pkgmgr.actions.install.pipeline.resolve_command_for_repo")
    def test_a_failed_hook_falls_back_to_the_next(
        self,
        mock_resolve_command_for_repo: MagicMock,
        mock_create_ink: MagicMock,
    ) -> None:
        """A hook that fails installed nothing, so the next one gets its turn."""
        mock_resolve_command_for_repo.return_value = None

        ctx = _minimal_context()
        broken = DummyInstaller(
            "makefile-installer",
            layer=CliLayer.MAKEFILE.value,
            supports_result=True,
            fails=True,
        )
        working = DummyInstaller(
            "python-installer",
            layer=CliLayer.PYTHON.value,
            supports_result=True,
        )

        pipeline = InstallationPipeline([broken, working])
        pipeline.run(ctx)

        self.assertTrue(broken.ran, "The preferred hook should be tried first.")
        self.assertTrue(
            working.ran,
            "The next hook must run when the preferred one installed nothing.",
        )

    @patch("pkgmgr.actions.install.pipeline.create_ink")
    @patch("pkgmgr.actions.install.pipeline.resolve_command_for_repo")
    def test_a_repository_whose_hooks_all_fail_is_reported(
        self,
        mock_resolve_command_for_repo: MagicMock,
        mock_create_ink: MagicMock,
    ) -> None:
        """Falling back must not turn a broken repository into a silent pass."""
        mock_resolve_command_for_repo.return_value = None

        ctx = _minimal_context()
        first = DummyInstaller(
            "makefile-installer",
            layer=CliLayer.MAKEFILE.value,
            supports_result=True,
            fails=True,
        )
        second = DummyInstaller(
            "python-installer",
            layer=CliLayer.PYTHON.value,
            supports_result=True,
            fails=True,
        )

        pipeline = InstallationPipeline([first, second])
        with self.assertRaises(SystemExit):
            pipeline.run(ctx)


if __name__ == "__main__":
    unittest.main()
