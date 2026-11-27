from __future__ import annotations

import io
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from pkgmgr.actions.release.git_ops import ensure_clean_and_synced
from pkgmgr.cli.context import CLIContext
from pkgmgr.cli.dispatch import dispatch_command
from pkgmgr.cli.parser import create_parser


def git(cwd: str, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


class TestReleaseCwdCheckout(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = Path(os.path.realpath(self._tmp.name))
        (root / "gitconfig").write_text(
            "[user]\n\tname = t\n\temail = t@example.org\n"
            "[commit]\n\tgpgsign = false\n"
            "[init]\n\tdefaultBranch = main\n"
        )
        env = patch.dict(
            os.environ,
            {"GIT_CONFIG_GLOBAL": str(root / "gitconfig"), "GIT_CONFIG_NOSYSTEM": "1"},
        )
        env.start()
        self.addCleanup(env.stop)
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)

        self.main = str(root / "app")
        git(str(root), "init", "-q", self.main)
        Path(self.main, "app.py").write_text("v1\n")
        git(self.main, "add", "app.py")
        git(self.main, "commit", "-q", "-m", "init")
        self.clone = os.path.join(self.main, ".worktrees", "release")
        git(str(root), "clone", "-q", self.main, self.clone)
        Path(self.main, "app.py").write_text("unfinished work\n")

        self.ctx = CLIContext(
            config_merged={},
            repositories_base_dir=str(root / "repos"),
            all_repositories=[
                {
                    "provider": "github.com",
                    "account": "t",
                    "repository": "app",
                    "directory": self.main,
                }
            ],
            binaries_dir=str(root / "bin"),
            user_config_path=str(root / "config.yaml"),
        )

    def _release_cwd(self, cwd: str, *argv: str) -> str:
        seen: list[str] = []
        os.chdir(cwd)
        args = create_parser("test").parse_args(["release", *argv, "--no-publish"])
        with (
            patch(
                "pkgmgr.cli.commands.release.run_release",
                side_effect=lambda **_kwargs: seen.append(os.getcwd()),
            ),
            redirect_stdout(io.StringIO()),
        ):
            dispatch_command(args, self.ctx)
        self.assertEqual(len(seen), 1)
        return seen[0]

    def test_release_from_a_nested_clone_runs_in_the_clone(self) -> None:
        self.assertEqual(self._release_cwd(self.clone, "patch"), self.clone)

    def test_explicit_identifier_keeps_the_configured_checkout(self) -> None:
        self.assertEqual(self._release_cwd(self.clone, "patch", "app"), self.main)

    def test_tracked_changes_refuse_the_release(self) -> None:
        os.chdir(self.main)

        with self.assertRaises(RuntimeError) as cm:
            ensure_clean_and_synced(preview=False)

        self.assertIn("app.py", str(cm.exception))
        self.assertEqual(Path(self.main, "app.py").read_text(), "unfinished work\n")

    def test_clean_clone_passes_the_check(self) -> None:
        os.chdir(self.clone)

        with redirect_stdout(io.StringIO()):
            ensure_clean_and_synced(preview=False)


if __name__ == "__main__":
    unittest.main()
