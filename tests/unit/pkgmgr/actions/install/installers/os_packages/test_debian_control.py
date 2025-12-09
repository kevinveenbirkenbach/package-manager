import unittest
from unittest.mock import patch

from pkgmgr.actions.repository.install.context import RepoContext
from pkgmgr.actions.repository.install.installers.os_packages.debian_control import (
    DebianControlInstaller,
)


class TestDebianControlInstaller(unittest.TestCase):
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
        self.installer = DebianControlInstaller()

    @patch("os.path.exists", return_value=True)
    @patch("shutil.which", return_value="/usr/bin/dpkg-buildpackage")
    def test_supports_true(self, mock_which, mock_exists):
        """
        supports() should return True when dpkg-buildpackage is available
        and a debian/control file exists in the repository.
        """
        self.assertTrue(self.installer.supports(self.ctx))

    @patch("os.path.exists", return_value=True)
    @patch("shutil.which", return_value=None)
    def test_supports_false_without_dpkg_buildpackage(self, mock_which, mock_exists):
        """
        supports() should return False when dpkg-buildpackage is not available,
        even if a debian/control file exists.
        """
        self.assertFalse(self.installer.supports(self.ctx))

    @patch(
        "pkgmgr.actions.repository.install.installers.os_packages.debian_control.run_command"
    )
    @patch("glob.glob", return_value=["/tmp/package-manager_0.1.1_all.deb"])
    @patch("os.path.exists", return_value=True)
    @patch("shutil.which")
    def test_run_builds_and_installs_debs(
        self,
        mock_which,
        mock_exists,
        mock_glob,
        mock_run_command,
    ):
        """
        run() should:

        1. Install build dependencies (apt-get build-dep).
        2. Build the package using dpkg-buildpackage -b -us -uc.
        3. Discover built .deb files via glob.
        4. Install the resulting .deb packages using a suitable tool:
           - dpkg -i
           - sudo dpkg -i
           - or sudo apt-get install -y
        """

        # Simulate dpkg-buildpackage and apt-get being available.
        def which_side_effect(name):
            if name == "dpkg-buildpackage":
                return "/usr/bin/dpkg-buildpackage"
            if name == "apt-get":
                return "/usr/bin/apt-get"
            return None

        mock_which.side_effect = which_side_effect

        self.installer.run(self.ctx)

        cmds = [c[0][0] for c in mock_run_command.call_args_list]

        # 1) apt-get update
        self.assertTrue(any("apt-get update" in cmd for cmd in cmds))

        # 2) apt-get build-dep -y ./ (with or without trailing space)
        self.assertTrue(
            any(
                "apt-get build-dep -y ./ " in cmd
                or "apt-get build-dep -y ./"
                in cmd
                for cmd in cmds
            )
        )

        # 3) dpkg-buildpackage -b -us -uc
        self.assertTrue(any("dpkg-buildpackage -b -us -uc" in cmd for cmd in cmds))

        # 4) final installation of .deb packages:
        #    accept dpkg -i, sudo dpkg -i, or sudo apt-get install -y
        has_plain_dpkg_install = any(cmd.startswith("dpkg -i ") for cmd in cmds)
        has_sudo_dpkg_install = any(cmd.startswith("sudo dpkg -i ") for cmd in cmds)
        has_apt_install = any(
            cmd.startswith("sudo apt-get install -y ") for cmd in cmds
        )

        self.assertTrue(
            has_plain_dpkg_install or has_sudo_dpkg_install or has_apt_install,
            msg=(
                "Expected one of 'dpkg -i', 'sudo dpkg -i' or "
                "'sudo apt-get install -y', but got commands: "
                f"{cmds}"
            ),
        )


if __name__ == "__main__":
    unittest.main()
