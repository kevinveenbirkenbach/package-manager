# tests/unit/pkgmgr/installers/test_base.py

import unittest
from pkgmgr.actions.repository.install.installers.base import BaseInstaller
from pkgmgr.actions.repository.install.context import RepoContext


class DummyInstaller(BaseInstaller):
    def __init__(self, supports_value: bool = True):
        self._supports_value = supports_value
        self.ran_with = None

    def supports(self, ctx: RepoContext) -> bool:
        return self._supports_value

    def run(self, ctx: RepoContext) -> None:
        self.ran_with = ctx


class TestBaseInstaller(unittest.TestCase):
    def test_dummy_installer_supports_and_run(self):
        ctx = RepoContext(
            repo={},
            identifier="id",
            repo_dir="/tmp/repo",
            repositories_base_dir="/tmp",
            bin_dir="/bin",
            all_repos=[],
            no_verification=False,
            preview=False,
            quiet=False,
            clone_mode="ssh",
            update_dependencies=False,
        )
        inst = DummyInstaller(supports_value=True)
        self.assertTrue(inst.supports(ctx))
        self.assertIsNone(inst.ran_with)
        inst.run(ctx)
        self.assertIs(inst.ran_with, ctx)


if __name__ == "__main__":
    unittest.main()
