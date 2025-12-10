import unittest
from unittest.mock import patch

from pkgmgr.actions.install.context import RepoContext
from pkgmgr.actions.install.installers.os_packages.rpm_spec import (
    RpmSpecInstaller,
)


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
        """
        supports() should return True when:
        - rpmbuild is available, and
        - at least one of dnf/yum/yum-builddep is available, and
        - a *.spec file is present in the repo.
        """

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
        """
        supports() should return False if no *.spec file is found,
        even if rpmbuild is present.
        """
        mock_which.return_value = "/usr/bin/rpmbuild"
        self.assertFalse(self.installer.supports(self.ctx))

    @patch.object(RpmSpecInstaller, "_prepare_source_tarball")
    @patch("pkgmgr.actions.install.installers.os_packages.rpm_spec.run_command")
    @patch("glob.glob")
    @patch("shutil.which")
    def test_run_builds_and_installs_rpms(
        self,
        mock_which,
        mock_glob,
        mock_run_command,
        mock_prepare_source_tarball,
    ):
        """
        run() should:

        1. Determine the .spec file in the repo.
        2. Call _prepare_source_tarball() once with ctx and spec path.
        3. Install build dependencies via dnf/yum-builddep/yum.
        4. Call rpmbuild -ba <spec>.
        5. Find built RPMs via glob.
        6. Install built RPMs via dnf/yum/rpm (here: dnf).
        """

        # glob.glob is used twice: once for *.spec, once for built RPMs.
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

        # _prepare_source_tarball must have been called with the resolved spec path.
        mock_prepare_source_tarball.assert_called_once_with(
            self.ctx,
            "/tmp/repo/package-manager.spec",
        )

        # Collect all command strings passed to run_command.
        cmds = [c[0][0] for c in mock_run_command.call_args_list]

        # 1) build dependencies (dnf builddep)
        self.assertTrue(any("builddep -y" in cmd for cmd in cmds))

        # 2) rpmbuild -ba <spec>
        self.assertTrue(any(cmd.startswith("rpmbuild -ba ") for cmd in cmds))

        # 3) installation via dnf: "sudo dnf install -y <rpms>"
        self.assertTrue(any(cmd.startswith("sudo dnf install -y ") for cmd in cmds))


if __name__ == "__main__":
    unittest.main()
