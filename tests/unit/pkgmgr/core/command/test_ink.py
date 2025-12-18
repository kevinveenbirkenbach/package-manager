import os
import tempfile
import unittest
from unittest.mock import patch

from pkgmgr.core.command.ink import create_ink


class TestCreateInk(unittest.TestCase):
    @patch("pkgmgr.core.command.ink.get_repo_dir")
    @patch("pkgmgr.core.command.ink.get_repo_identifier")
    def test_self_referential_command_skips_symlink(
        self,
        mock_get_repo_identifier,
        mock_get_repo_dir,
    ):
        """
        If the resolved command path is identical to the final link target,
        create_ink() must NOT replace it with a self-referential symlink.

        This simulates the situation where the command already lives at
        ~/.local/bin/<identifier> and we would otherwise create a symlink
        pointing to itself.
        """
        mock_get_repo_identifier.return_value = "package-manager"
        mock_get_repo_dir.return_value = "/fake/repo"

        with tempfile.TemporaryDirectory() as bin_dir:
            # Simulate an existing real binary at the final link location.
            command_path = os.path.join(bin_dir, "package-manager")
            with open(command_path, "w", encoding="utf-8") as f:
                f.write("#!/bin/sh\necho package-manager\n")

            # Sanity check: not a symlink yet.
            self.assertTrue(os.path.exists(command_path))
            self.assertFalse(os.path.islink(command_path))

            repo = {"command": command_path}

            # This must NOT turn the file into a self-referential symlink.
            create_ink(
                repo=repo,
                repositories_base_dir="/fake/base",
                bin_dir=bin_dir,
                all_repos=[],
                quiet=True,
                preview=False,
            )

            # After create_ink(), the file must still exist and must not be a symlink.
            self.assertTrue(os.path.exists(command_path))
            self.assertFalse(
                os.path.islink(command_path),
                "create_ink() must not create a self-referential symlink "
                "when command == link_path",
            )

    @patch("pkgmgr.core.command.ink.get_repo_dir")
    @patch("pkgmgr.core.command.ink.get_repo_identifier")
    def test_create_symlink_for_normal_command(
        self,
        mock_get_repo_identifier,
        mock_get_repo_dir,
    ):
        """
        In the normal case (command path != link target), create_ink()
        must create a symlink in bin_dir pointing to the given command,
        and optionally an alias symlink when repo['alias'] is set.
        """
        mock_get_repo_identifier.return_value = "mytool"

        with (
            tempfile.TemporaryDirectory() as repo_dir,
            tempfile.TemporaryDirectory() as bin_dir,
        ):
            mock_get_repo_dir.return_value = repo_dir

            # Create a fake executable inside the repository.
            command_path = os.path.join(repo_dir, "main.sh")
            with open(command_path, "w", encoding="utf-8") as f:
                f.write("#!/bin/sh\necho mytool\n")
            os.chmod(command_path, 0o755)

            repo = {
                "command": command_path,
                "alias": "mt",
            }

            create_ink(
                repo=repo,
                repositories_base_dir="/fake/base",
                bin_dir=bin_dir,
                all_repos=[],
                quiet=True,
                preview=False,
            )

            link_path = os.path.join(bin_dir, "mytool")
            alias_path = os.path.join(bin_dir, "mt")

            # Main link must exist and point to the command.
            self.assertTrue(os.path.islink(link_path))
            self.assertEqual(os.readlink(link_path), command_path)

            # Alias must exist and point to the main link.
            self.assertTrue(os.path.islink(alias_path))
            self.assertEqual(os.readlink(alias_path), link_path)


if __name__ == "__main__":
    unittest.main()
