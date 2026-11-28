from __future__ import annotations

import io
import os
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pkgmgr.actions.release.git_ops import ensure_clean_and_synced
from pkgmgr.cli.context import CLIContext


class TestIntegrationReleasePublishHook(unittest.TestCase):
    def _ctx(self) -> SimpleNamespace:
        # Minimal CLIContext shape used by handle_release()
        return SimpleNamespace(
            repositories_base_dir="/tmp",
            all_repositories=[],
        )

    def _parse(self, argv: list[str]):
        from pkgmgr.cli.parser import create_parser

        parser = create_parser("pkgmgr test")
        return parser.parse_args(argv)

    def test_release_runs_publish_by_default_and_respects_tty(self) -> None:
        from pkgmgr.cli.commands.release import handle_release

        with tempfile.TemporaryDirectory() as td:
            selected = [{"directory": td}]

            # Go through real parser to ensure CLI surface is wired correctly
            args = self._parse(["release", "patch"])

            with (
                patch("pkgmgr.cli.commands.release.run_release") as m_release,
                patch("pkgmgr.cli.commands.release.run_publish") as m_publish,
                patch(
                    "pkgmgr.cli.commands.release.sys.stdin.isatty", return_value=False
                ),
            ):
                handle_release(args=args, ctx=self._ctx(), selected=selected)

            m_release.assert_called_once()
            m_publish.assert_called_once()

            _, kwargs = m_publish.call_args
            self.assertEqual(kwargs["repo"], selected[0])
            self.assertEqual(kwargs["repo_dir"], td)
            self.assertFalse(kwargs["interactive"])
            self.assertFalse(kwargs["allow_prompt"])

    def test_release_skips_publish_when_no_publish_flag_set(self) -> None:
        from pkgmgr.cli.commands.release import handle_release

        with tempfile.TemporaryDirectory() as td:
            selected = [{"directory": td}]

            args = self._parse(["release", "patch", "--no-publish"])

            with (
                patch("pkgmgr.cli.commands.release.run_release") as m_release,
                patch("pkgmgr.cli.commands.release.run_publish") as m_publish,
            ):
                handle_release(args=args, ctx=self._ctx(), selected=selected)

            m_release.assert_called_once()
            m_publish.assert_not_called()


class TestReleaseCwdCheckout(unittest.TestCase):
    def _sh(self, cwd: str, *argv: str) -> None:
        subprocess.run(["git", *argv], cwd=cwd, check=True, capture_output=True)

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = os.path.realpath(self._tmp.name)
        identity = {
            f"GIT_{role}_{field}": value
            for role in ("AUTHOR", "COMMITTER")
            for field, value in (("NAME", "t"), ("EMAIL", "t@example.org"))
        }
        scrubbed = patch.dict(
            os.environ,
            {**identity, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"},
        )
        scrubbed.start()
        self.addCleanup(scrubbed.stop)
        self.addCleanup(os.chdir, os.getcwd())

        self.main = os.path.join(base, "app")
        self._sh(base, "init", "-q", "-b", "main", self.main)
        Path(self.main, "app.py").write_text("v1\n")
        self._sh(self.main, "add", "app.py")
        self._sh(self.main, "commit", "-q", "--no-gpg-sign", "-m", "init")
        self.clone = os.path.join(self.main, ".worktrees", "release")
        self._sh(base, "clone", "-q", self.main, self.clone)
        Path(self.main, "app.py").write_text("unfinished work\n")
        self.ctx = CLIContext(
            config_merged={},
            repositories_base_dir=os.path.join(base, "repos"),
            all_repositories=[
                {
                    "provider": "github.com",
                    "account": "t",
                    "repository": "app",
                    "directory": self.main,
                }
            ],
            binaries_dir=os.path.join(base, "bin"),
            user_config_path=os.path.join(base, "config.yaml"),
        )

    def _released_in(self, cwd: str, *argv: str) -> str:
        from pkgmgr.cli.dispatch import dispatch_command
        from pkgmgr.cli.parser import create_parser

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
        self.assertEqual(self._released_in(self.clone, "patch"), self.clone)

    def test_explicit_identifier_keeps_the_configured_checkout(self) -> None:
        self.assertEqual(self._released_in(self.clone, "patch", "app"), self.main)

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
