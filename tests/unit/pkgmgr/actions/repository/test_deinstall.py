import unittest
from unittest.mock import patch

from pkgmgr.actions.repository.deinstall import deinstall_repos


class TestDeinstallRepos(unittest.TestCase):
    def test_preview_removes_nothing_but_runs_make_if_makefile_exists(self):
        repo = {
            "provider": "github.com",
            "account": "alice",
            "repository": "demo",
            "alias": "demo",
        }
        selected = [repo]

        with (
            patch(
                "pkgmgr.actions.repository.deinstall.get_repo_identifier",
                return_value="demo",
            ),
            patch(
                "pkgmgr.actions.repository.deinstall.get_repo_dir",
                return_value="/repos/github.com/alice/demo",
            ),
            patch(
                "pkgmgr.actions.repository.deinstall.os.path.expanduser",
                return_value="/home/u/.local/bin",
            ),
            patch("pkgmgr.actions.repository.deinstall.os.path.exists") as mock_exists,
            patch("pkgmgr.actions.repository.deinstall.os.remove") as mock_remove,
            patch("pkgmgr.actions.repository.deinstall.run_command") as mock_run,
            patch("builtins.input", return_value="y"),
        ):
            # alias exists, Makefile exists
            def exists_side_effect(path):
                if path == "/home/u/.local/bin/demo":
                    return True
                if path == "/repos/github.com/alice/demo/Makefile":
                    return True
                return False

            mock_exists.side_effect = exists_side_effect

            deinstall_repos(
                selected_repos=selected,
                repositories_base_dir="/repos",
                bin_dir="~/.local/bin",
                all_repos=selected,
                preview=True,
            )

            # Preview: do not remove
            mock_remove.assert_not_called()

            # But still "would run" make deinstall via run_command (preview=True)
            mock_run.assert_called_once_with(
                "make deinstall",
                cwd="/repos/github.com/alice/demo",
                preview=True,
            )

    def test_non_preview_removes_alias_when_confirmed(self):
        repo = {
            "provider": "github.com",
            "account": "alice",
            "repository": "demo",
            "alias": "demo",
        }
        selected = [repo]

        with (
            patch(
                "pkgmgr.actions.repository.deinstall.get_repo_identifier",
                return_value="demo",
            ),
            patch(
                "pkgmgr.actions.repository.deinstall.get_repo_dir",
                return_value="/repos/github.com/alice/demo",
            ),
            patch(
                "pkgmgr.actions.repository.deinstall.os.path.expanduser",
                return_value="/home/u/.local/bin",
            ),
            patch("pkgmgr.actions.repository.deinstall.os.path.exists") as mock_exists,
            patch("pkgmgr.actions.repository.deinstall.os.remove") as mock_remove,
            patch("pkgmgr.actions.repository.deinstall.run_command") as mock_run,
            patch("builtins.input", return_value="y"),
        ):
            # alias exists, Makefile does NOT exist
            def exists_side_effect(path):
                if path == "/home/u/.local/bin/demo":
                    return True
                if path == "/repos/github.com/alice/demo/Makefile":
                    return False
                return False

            mock_exists.side_effect = exists_side_effect

            deinstall_repos(
                selected_repos=selected,
                repositories_base_dir="/repos",
                bin_dir="~/.local/bin",
                all_repos=selected,
                preview=False,
            )

            mock_remove.assert_called_once_with("/home/u/.local/bin/demo")
            mock_run.assert_not_called()
