import os
import unittest
from unittest import mock
from unittest.mock import patch

from pkgmgr.actions.repository.install.context import RepoContext
from pkgmgr.actions.repository.install.installers.nix_flake import NixFlakeInstaller


class TestNixFlakeInstaller(unittest.TestCase):
    def setUp(self):
        self.repo = {"name": "test-repo"}
        self.ctx = RepoContext(
            repo=self.repo,
            identifier="test-id",
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
        self.installer = NixFlakeInstaller()

    @patch("shutil.which", return_value="/usr/bin/nix")
    @patch("os.path.exists", return_value=True)
    def test_supports_true_when_nix_and_flake_exist(self, mock_exists, mock_which):
        self.assertTrue(self.installer.supports(self.ctx))
        mock_which.assert_called_with("nix")
        mock_exists.assert_called_with(os.path.join(self.ctx.repo_dir, "flake.nix"))

    @patch("shutil.which", return_value=None)
    @patch("os.path.exists", return_value=True)
    def test_supports_false_when_nix_missing(self, mock_exists, mock_which):
        self.assertFalse(self.installer.supports(self.ctx))

    @patch("os.path.exists", return_value=True)
    @patch("shutil.which", return_value="/usr/bin/nix")
    @mock.patch("pkgmgr.actions.repository.install.installers.nix_flake.run_command")
    def test_run_removes_old_profile_and_installs_outputs(
        self,
        mock_run_command,
        mock_which,
        mock_exists,
    ):
        """
        Ensure that run():
          - first tries to remove the old 'package-manager' profile entry
          - then installs both 'pkgmgr' and 'default' outputs.
        """
        cmds = []

        def side_effect(cmd, cwd=None, preview=False, *args, **kwargs):
            cmds.append(cmd)
            return None

        mock_run_command.side_effect = side_effect

        self.installer.run(self.ctx)

        remove_cmd = f"nix profile remove {self.installer.PROFILE_NAME} || true"
        install_pkgmgr_cmd = f"nix profile install {self.ctx.repo_dir}#pkgmgr"
        install_default_cmd = f"nix profile install {self.ctx.repo_dir}#default"

        # Mindestens diese drei Kommandos müssen aufgerufen worden sein
        self.assertIn(remove_cmd, cmds)
        self.assertIn(install_pkgmgr_cmd, cmds)
        self.assertIn(install_default_cmd, cmds)

        # Optional: sicherstellen, dass der remove-Aufruf zuerst kam
        self.assertEqual(cmds[0], remove_cmd)

    @patch("shutil.which", return_value="/usr/bin/nix")
    @mock.patch("pkgmgr.actions.repository.install.installers.nix_flake.run_command")
    def test_ensure_old_profile_removed_ignores_systemexit(
        self,
        mock_run_command,
        mock_which,
    ):
        """
        _ensure_old_profile_removed() must not propagate SystemExit, even if
        'nix profile remove' fails (e.g. profile entry does not exist).
        """

        def side_effect(cmd, cwd=None, preview=False, *args, **kwargs):
            raise SystemExit(1)

        mock_run_command.side_effect = side_effect

        # Should not raise, SystemExit is swallowed internally.
        self.installer._ensure_old_profile_removed(self.ctx)

        remove_cmd = f"nix profile remove {self.installer.PROFILE_NAME} || true"
        mock_run_command.assert_called_with(
            remove_cmd,
            cwd=self.ctx.repo_dir,
            preview=self.ctx.preview,
        )


if __name__ == "__main__":
    unittest.main()
