# tests/integration/test_install_repos_integration.py

import os
import tempfile
import unittest
from unittest.mock import patch

import pkgmgr.install_repos as install_module
from pkgmgr.install_repos import install_repos
from pkgmgr.installers.base import BaseInstaller


class DummyInstaller(BaseInstaller):
    """
    Minimal installer used to ensure that the installation pipeline runs
    without executing any real external commands.
    """

    layer = None

    def supports(self, ctx):
        return True

    def run(self, ctx):
        return


class TestInstallReposIntegration(unittest.TestCase):
    @patch("pkgmgr.install_repos.verify_repository")
    @patch("pkgmgr.install_repos.clone_repos")
    @patch("pkgmgr.install_repos.get_repo_dir")
    @patch("pkgmgr.install_repos.get_repo_identifier")
    def test_system_binary_vs_nix_binary(
        self,
        mock_get_repo_identifier,
        mock_get_repo_dir,
        mock_clone_repos,
        mock_verify_repository,
    ):
        """
        Full integration test for high-level command resolution + symlink creation.

        We do NOT re-test all low-level file-system details of
        resolve_command_for_repo here (that is covered by unit tests).
        Instead, we assert that:

          - If resolve_command_for_repo(...) returns None:
              → install_repos() does NOT create a symlink.

          - If resolve_command_for_repo(...) returns a path:
              → install_repos() creates exactly one symlink in bin_dir
                that points to this path.

        Concretely:

          - repo-system:
              resolve_command_for_repo(...) → None
              → no symlink in bin_dir for this repo.

          - repo-nix:
              resolve_command_for_repo(...) → "/nix/profile/bin/repo-nix"
              → exactly one symlink in bin_dir pointing to that path.
        """
        # Repositories must have provider/account/repository so that get_repo_dir()
        # does not crash when called from create_ink().
        repo_system = {
            "name": "repo-system",
            "provider": "github.com",
            "account": "dummy",
            "repository": "repo-system",
        }
        repo_nix = {
            "name": "repo-nix",
            "provider": "github.com",
            "account": "dummy",
            "repository": "repo-nix",
        }

        selected_repos = [repo_system, repo_nix]
        all_repos = selected_repos

        with tempfile.TemporaryDirectory() as tmp_base, \
             tempfile.TemporaryDirectory() as tmp_bin:

            # Fake repo directories (what get_repo_dir will return)
            repo_system_dir = os.path.join(tmp_base, "repo-system")
            repo_nix_dir = os.path.join(tmp_base, "repo-nix")
            os.makedirs(repo_system_dir, exist_ok=True)
            os.makedirs(repo_nix_dir, exist_ok=True)

            # Identifiers and repo dirs used inside install_repos()
            mock_get_repo_identifier.side_effect = ["repo-system", "repo-nix"]
            mock_get_repo_dir.side_effect = [repo_system_dir, repo_nix_dir]

            # Repository verification always succeeds
            mock_verify_repository.return_value = (True, [], "commit", "key")
            mock_clone_repos.return_value = None

            # Pretend this is the "Nix binary" path for repo-nix
            nix_tool_path = "/nix/profile/bin/repo-nix"

            # Patch resolve_command_for_repo at the install_repos module level
            with patch("pkgmgr.install_repos.resolve_command_for_repo") as mock_resolve, \
                 patch("pkgmgr.install_repos.os.path.exists") as mock_exists_install:

                def fake_resolve_command(repo, repo_identifier: str, repo_dir: str):
                    """
                    High-level behavior stub:

                      - For repo-system: act as if a system package owns the command
                        → return None (no symlink).

                      - For repo-nix: act as if a Nix profile binary is the entrypoint
                        → return nix_tool_path (symlink should be created).
                    """
                    if repo_identifier == "repo-system":
                        return None
                    if repo_identifier == "repo-nix":
                        return nix_tool_path
                    return None

                def fake_exists_install(path: str) -> bool:
                    """
                    Make _ensure_repo_dir() believe that the repo directories
                    already exist so that it does not attempt cloning.
                    """
                    if path in (repo_system_dir, repo_nix_dir):
                        return True
                    return False

                mock_resolve.side_effect = fake_resolve_command
                mock_exists_install.side_effect = fake_exists_install

                # Use only DummyInstaller so we focus on link creation, not installer behavior
                old_installers = install_module.INSTALLERS
                install_module.INSTALLERS = [DummyInstaller()]
                try:
                    install_repos(
                        selected_repos=selected_repos,
                        repositories_base_dir=tmp_base,
                        bin_dir=tmp_bin,
                        all_repos=all_repos,
                        no_verification=False,
                        preview=False,
                        quiet=False,
                        clone_mode="shallow",
                        update_dependencies=False,
                    )
                finally:
                    install_module.INSTALLERS = old_installers

            # ------------------------------------------------------------------
            # Inspect bin_dir: exactly one symlink must exist, pointing to Nix.
            # ------------------------------------------------------------------
            symlink_paths = []
            for entry in os.listdir(tmp_bin):
                full = os.path.join(tmp_bin, entry)
                if os.path.islink(full):
                    symlink_paths.append(full)

            # There must be exactly one symlink (for repo-nix)
            self.assertEqual(
                len(symlink_paths),
                1,
                f"Expected exactly one symlink in {tmp_bin}, found {symlink_paths}",
            )

            target = os.readlink(symlink_paths[0])

            # That symlink must point to the "Nix" path returned by the resolver stub
            self.assertEqual(
                target,
                nix_tool_path,
                f"Expected symlink target to be Nix binary {nix_tool_path}, got {target}",
            )


if __name__ == "__main__":
    unittest.main()
