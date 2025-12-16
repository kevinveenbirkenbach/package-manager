# tests/integration/test_repos_create_pypi_not_in_git_config.py
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pkgmgr.actions.repository.create import create_repo


class TestCreateRepoPypiNotInGitConfig(unittest.TestCase):
    def test_create_repo_writes_pypi_to_mirrors_but_not_git_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)

            # Repositories base dir used by create flow
            repos_base = tmp_path / "Repositories"
            user_cfg = tmp_path / "user.yml"
            bin_dir = tmp_path / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)

            cfg = {
                "directories": {"repositories": str(repos_base)},
                "repositories": [],
            }

            # Provide a minimal templates directory so TemplateRenderer can run
            tpl_dir = tmp_path / "tpl"
            tpl_dir.mkdir(parents=True, exist_ok=True)
            (tpl_dir / "README.md.j2").write_text(
                "# {{ repository }}\n", encoding="utf-8"
            )

            # Expected repo dir for identifier github.com/acme/repo
            repo_dir = repos_base / "github.com" / "acme" / "repo"

            with (
                # Avoid any real network calls during mirror "remote probing"
                patch(
                    "pkgmgr.actions.mirror.setup_cmd.probe_remote_reachable",
                    return_value=True,
                ),
                # Force templates to come from our temp directory
                patch(
                    "pkgmgr.actions.repository.create.templates.TemplateRenderer._resolve_templates_dir",
                    return_value=str(tpl_dir),
                ),
                # Make git commit deterministic without depending on global git config
                patch.dict(
                    os.environ,
                    {
                        "GIT_AUTHOR_NAME": "Test Author",
                        "GIT_AUTHOR_EMAIL": "author@example.invalid",
                        "GIT_COMMITTER_NAME": "Test Author",
                        "GIT_COMMITTER_EMAIL": "author@example.invalid",
                    },
                    clear=False,
                ),
            ):
                create_repo(
                    "github.com/acme/repo",
                    cfg,
                    str(user_cfg),
                    str(bin_dir),
                    remote=False,
                    preview=False,
                )

            # --- Assertions: MIRRORS file ---
            mirrors_file = repo_dir / "MIRRORS"
            self.assertTrue(mirrors_file.exists(), "MIRRORS file was not created")

            mirrors_content = mirrors_file.read_text(encoding="utf-8")
            self.assertIn(
                "pypi https://pypi.org/project/repo/",
                mirrors_content,
                "PyPI mirror entry must exist in MIRRORS",
            )
            self.assertIn(
                "origin git@github.com:acme/repo.git",
                mirrors_content,
                "origin SSH URL must exist in MIRRORS",
            )

            # --- Assertions: git config must NOT contain PyPI ---
            git_config = repo_dir / ".git" / "config"
            self.assertTrue(git_config.exists(), ".git/config was not created")

            git_config_content = git_config.read_text(encoding="utf-8")
            self.assertNotIn(
                "pypi.org/project",
                git_config_content,
                "PyPI must never be written into git config",
            )

            # --- Assertions: origin remote exists and points to SSH ---
            remotes = subprocess.check_output(
                ["git", "-C", str(repo_dir), "remote"],
                text=True,
            ).splitlines()

            self.assertIn("origin", remotes, "origin remote was not created")

            remote_v = subprocess.check_output(
                ["git", "-C", str(repo_dir), "remote", "-v"],
                text=True,
            )
            self.assertIn("git@github.com:acme/repo.git", remote_v)


if __name__ == "__main__":
    unittest.main()
