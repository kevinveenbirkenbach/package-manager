# tests/unit/pkgmgr/test_resolve_command.py

import unittest
from unittest.mock import patch

import pkgmgr.core.command.resolve as resolve_command_module


class TestResolveCommandForRepo(unittest.TestCase):
    def test_explicit_command_wins(self):
        repo = {"command": "/custom/cmd"}
        result = resolve_command_module.resolve_command_for_repo(
            repo=repo,
            repo_identifier="tool",
            repo_dir="/repos/tool",
        )
        self.assertEqual(result, "/custom/cmd")

    @patch("pkgmgr.core.command.resolve.shutil.which", return_value="/usr/bin/tool")
    def test_system_binary_returns_none_and_no_error(self, mock_which):
        repo = {}
        result = resolve_command_module.resolve_command_for_repo(
            repo=repo,
            repo_identifier="tool",
            repo_dir="/repos/tool",
        )
        # System binary → no link
        self.assertIsNone(result)

    @patch("pkgmgr.core.command.resolve.os.access")
    @patch("pkgmgr.core.command.resolve.os.path.exists")
    @patch("pkgmgr.core.command.resolve.shutil.which", return_value=None)
    @patch("pkgmgr.core.command.resolve.os.path.expanduser", return_value="/fakehome")
    def test_nix_profile_binary(
        self,
        mock_expanduser,
        mock_which,
        mock_exists,
        mock_access,
    ):
        """
        No system/PATH binary, but a Nix profile binary exists:
        → must return the Nix binary path.
        """
        repo = {}
        fake_home = "/fakehome"
        nix_path = f"{fake_home}/.nix-profile/bin/tool"

        def fake_exists(path):
            # Only the Nix binary exists
            return path == nix_path

        def fake_access(path, mode):
            # Only the Nix binary is executable
            return path == nix_path

        mock_exists.side_effect = fake_exists
        mock_access.side_effect = fake_access

        result = resolve_command_module.resolve_command_for_repo(
            repo=repo,
            repo_identifier="tool",
            repo_dir="/repos/tool",
        )
        self.assertEqual(result, nix_path)

    @patch("pkgmgr.core.command.resolve.os.access")
    @patch("pkgmgr.core.command.resolve.os.path.exists")
    @patch("pkgmgr.core.command.resolve.os.path.expanduser", return_value="/home/user")
    @patch("pkgmgr.core.command.resolve.shutil.which", return_value="/home/user/.local/bin/tool")
    def test_non_system_binary_on_path(
        self,
        mock_which,
        mock_expanduser,
        mock_exists,
        mock_access,
    ):
        """
        No system (/usr) binary and no Nix binary, but a non-system
        PATH binary exists (e.g. venv or ~/.local/bin):
        → must return that PATH binary.
        """
        repo = {}
        non_system_path = "/home/user/.local/bin/tool"
        nix_candidate = "/home/user/.nix-profile/bin/tool"

        def fake_exists(path):
            # Only the non-system PATH binary "exists".
            return path == non_system_path

        def fake_access(path, mode):
            # Only the non-system PATH binary is executable.
            return path == non_system_path

        mock_exists.side_effect = fake_exists
        mock_access.side_effect = fake_access

        result = resolve_command_module.resolve_command_for_repo(
            repo=repo,
            repo_identifier="tool",
            repo_dir="/repos/tool",
        )
        self.assertEqual(result, non_system_path)

    @patch("pkgmgr.core.command.resolve.os.access")
    @patch("pkgmgr.core.command.resolve.os.path.exists")
    @patch("pkgmgr.core.command.resolve.shutil.which", return_value=None)
    @patch("pkgmgr.core.command.resolve.os.path.expanduser", return_value="/fakehome")
    def test_fallback_to_main_py(
        self,
        mock_expanduser,
        mock_which,
        mock_exists,
        mock_access,
    ):
        """
        No system/non-system PATH binary, no Nix binary, but main.py exists:
        → must fall back to main.py in the repo.
        """
        repo = {}
        main_py = "/repos/tool/main.py"

        def fake_exists(path):
            return path == main_py

        def fake_access(path, mode):
            return path == main_py

        mock_exists.side_effect = fake_exists
        mock_access.side_effect = fake_access

        result = resolve_command_module.resolve_command_for_repo(
            repo=repo,
            repo_identifier="tool",
            repo_dir="/repos/tool",
        )
        self.assertEqual(result, main_py)

    @patch("pkgmgr.core.command.resolve.os.access", return_value=False)
    @patch("pkgmgr.core.command.resolve.os.path.exists", return_value=False)
    @patch("pkgmgr.core.command.resolve.shutil.which", return_value=None)
    @patch("pkgmgr.core.command.resolve.os.path.expanduser", return_value="/fakehome")
    def test_no_command_results_in_system_exit(
        self,
        mock_expanduser,
        mock_which,
        mock_exists,
        mock_access,
    ):
        """
        Nothing available at any layer:
        → must raise SystemExit with a descriptive error message.
        """
        repo = {}
        with self.assertRaises(SystemExit) as cm:
            resolve_command_module.resolve_command_for_repo(
                repo=repo,
                repo_identifier="tool",
                repo_dir="/repos/tool",
            )
        msg = str(cm.exception)
        self.assertIn("No executable command could be resolved for repository 'tool'", msg)


if __name__ == "__main__":
    unittest.main()
