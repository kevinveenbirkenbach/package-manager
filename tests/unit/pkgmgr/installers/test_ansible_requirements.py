# tests/unit/pkgmgr/installers/test_ansible_requirements.py

import os
import unittest
from unittest.mock import patch, mock_open

from pkgmgr.context import RepoContext
from pkgmgr.installers.ansible_requirements import AnsibleRequirementsInstaller


class TestAnsibleRequirementsInstaller(unittest.TestCase):
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
        self.installer = AnsibleRequirementsInstaller()

    @patch("os.path.exists", return_value=True)
    def test_supports_true_when_requirements_exist(self, mock_exists):
        self.assertTrue(self.installer.supports(self.ctx))
        mock_exists.assert_called_with(os.path.join(self.ctx.repo_dir, "requirements.yml"))

    @patch("os.path.exists", return_value=False)
    def test_supports_false_when_requirements_missing(self, mock_exists):
        self.assertFalse(self.installer.supports(self.ctx))

    @patch("pkgmgr.installers.ansible_requirements.run_command")
    @patch("tempfile.NamedTemporaryFile")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="""
collections:
  - name: community.docker
roles:
  - src: geerlingguy.docker
""",
    )
    @patch("os.path.exists", return_value=True)
    def test_run_installs_collections_and_roles(
        self, mock_exists, mock_file, mock_tmp, mock_run_command
    ):
        # Fake temp file name
        mock_tmp().__enter__().name = "/tmp/req.yml"

        self.installer.run(self.ctx)

        cmds = [call[0][0] for call in mock_run_command.call_args_list]
        self.assertIn(
            "ansible-galaxy collection install -r /tmp/req.yml",
            cmds,
        )
        self.assertIn(
            "ansible-galaxy role install -r /tmp/req.yml",
            cmds,
        )


if __name__ == "__main__":
    unittest.main()
