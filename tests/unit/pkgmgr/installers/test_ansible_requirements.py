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

    # --- Neue Tests für den Validator -------------------------------------

    @patch("pkgmgr.installers.ansible_requirements.run_command")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="""
- not:
  - a: mapping
""",
    )
    @patch("os.path.exists", return_value=True)
    def test_run_raises_when_top_level_is_not_mapping(
        self, mock_exists, mock_file, mock_run_command
    ):
        # YAML ist eine Liste -> Validator soll fehlschlagen
        with self.assertRaises(SystemExit):
            self.installer.run(self.ctx)

        mock_run_command.assert_not_called()

    @patch("pkgmgr.installers.ansible_requirements.run_command")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="""
collections: community.docker
roles:
  - src: geerlingguy.docker
""",
    )
    @patch("os.path.exists", return_value=True)
    def test_run_raises_when_collections_is_not_list(
        self, mock_exists, mock_file, mock_run_command
    ):
        # collections ist ein String statt Liste -> invalid
        with self.assertRaises(SystemExit):
            self.installer.run(self.ctx)

        mock_run_command.assert_not_called()

    @patch("pkgmgr.installers.ansible_requirements.run_command")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="""
collections:
  - name: community.docker
roles:
  - version: "latest"
""",
    )
    @patch("os.path.exists", return_value=True)
    def test_run_raises_when_role_mapping_has_no_name(
        self, mock_exists, mock_file, mock_run_command
    ):
        # roles-Eintrag ist Mapping ohne 'name' -> invalid
        with self.assertRaises(SystemExit):
            self.installer.run(self.ctx)

        mock_run_command.assert_not_called()

    @patch("pkgmgr.installers.ansible_requirements.run_command")
    @patch("tempfile.NamedTemporaryFile")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="""
collections:
  - name: community.docker
extra_key: should_be_ignored_but_warned
""",
    )
    @patch("os.path.exists", return_value=True)
    def test_run_accepts_unknown_top_level_keys(
        self, mock_exists, mock_file, mock_tmp, mock_run_command
    ):
        """
        Unknown top-level keys (z.B. 'extra_key') sollen nur eine Warnung
        auslösen, aber keine Validation-Exception.
        """
        mock_tmp().__enter__().name = "/tmp/req.yml"

        # Erwartung: kein SystemExit, run_command wird für collections aufgerufen
        self.installer.run(self.ctx)

        cmds = [call[0][0] for call in mock_run_command.call_args_list]
        self.assertIn(
            "ansible-galaxy collection install -r /tmp/req.yml",
            cmds,
        )
        # Keine roles definiert -> kein role-install
        self.assertNotIn(
            "ansible-galaxy role install -r /tmp/req.yml",
            cmds,
        )


if __name__ == "__main__":
    unittest.main()
