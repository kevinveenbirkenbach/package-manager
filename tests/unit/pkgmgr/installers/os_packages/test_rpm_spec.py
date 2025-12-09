# tests/unit/pkgmgr/installers/os_packages/test_rpm_spec.py

import unittest
from unittest.mock import patch

from pkgmgr.actions.repository.install.context import RepoContext
from pkgmgr.actions.repository.install.installers.os_packages.rpm_spec import RpmSpecInstaller


class TestRpmSpecInstaller(unittest.TestCase):
    def setUp(self):
        self.repo = {"name": "repo"}
        self.ctx = RepoContext(
            repo=self.repo,
            identifier="id",
            repo_dir="/tmp/repo",
            repositories_base_dir="/tmp",
            bin_dir="/bin",
            all_repos=[self.repo],
            no_verification=False,
            preview=False,
            quiet=False,
            clone_mode="ssh",
            update_dependencies=False,
        )
        self.installer = RpmSpecInstaller()

    @patch("glob.glob", return_value=["/tmp/repo/test.spec"])
    @patch("shutil.which")
    def test_supports_true(self, mock_which, mock_glob):
        def which_side_effect(name):
            if name == "rpmbuild":
                return "/usr/bin/rpmbuild"
            if name == "dnf":
                return "/usr/bin/dnf"
            return None

        mock_which.side_effect = which_side_effect

        self.assertTrue(self.installer.supports(self.ctx))

    @patch("glob.glob", return_value=[])
    @patch("shutil.which")
    def test_supports_false_missing_spec(self, mock_which, mock_glob):
        mock_which.return_value = "/usr/bin/rpmbuild"
        self.assertFalse(self.installer.supports(self.ctx))

    @patch("pkgmgr.actions.repository.install.installers.os_packages.rpm_spec.run_command")
    @patch("glob.glob")
    @patch("shutil.which")
    def test_run_builds_and_installs_rpms(
        self,
        mock_which,
        mock_glob,
        mock_run_command,
    ):
        # glob.glob wird zweimal benutzt: einmal für *.spec, einmal für gebaute RPMs
        def glob_side_effect(pattern, recursive=False):
            if pattern.endswith("*.spec"):
                return ["/tmp/repo/package-manager.spec"]
            if "rpmbuild/RPMS" in pattern:
                return ["/home/user/rpmbuild/RPMS/x86_64/package-manager-0.1.1.rpm"]
            return []

        mock_glob.side_effect = glob_side_effect

        def which_side_effect(name):
            if name == "rpmbuild":
                return "/usr/bin/rpmbuild"
            if name == "dnf":
                return "/usr/bin/dnf"
            if name == "rpm":
                return "/usr/bin/rpm"
            return None

        mock_which.side_effect = which_side_effect

        self.installer.run(self.ctx)

        cmds = [c[0][0] for c in mock_run_command.call_args_list]

        # 1) builddep
        self.assertTrue(any("builddep -y" in cmd for cmd in cmds))

        # 2) rpmbuild -ba
        self.assertTrue(any(cmd.startswith("rpmbuild -ba ") for cmd in cmds))

        # 3) rpm -i …
        self.assertTrue(any(cmd.startswith("sudo rpm -i ") for cmd in cmds))


if __name__ == "__main__":
    unittest.main()
