from __future__ import annotations

import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch


class TestCLIReleasePublishHook(unittest.TestCase):
    def _ctx(self) -> SimpleNamespace:
        # Minimal CLIContext shape used by handle_release
        return SimpleNamespace(
            repositories_base_dir="/tmp",
            all_repositories=[],
        )

    def test_release_runs_publish_by_default_and_respects_tty(self) -> None:
        from pkgmgr.cli.commands.release import handle_release

        with tempfile.TemporaryDirectory() as td:
            repo = {"directory": td}

            args = SimpleNamespace(
                list=False,
                release_type="patch",
                message=None,
                preview=False,
                force=False,
                close=False,
                no_publish=False,
            )

            with (
                patch("pkgmgr.cli.commands.release.run_release") as m_release,
                patch("pkgmgr.cli.commands.release.run_publish") as m_publish,
                patch(
                    "pkgmgr.cli.commands.release.sys.stdin.isatty", return_value=False
                ),
            ):
                handle_release(args=args, ctx=self._ctx(), selected=[repo])

            m_release.assert_called_once()
            m_publish.assert_called_once()

            _, kwargs = m_publish.call_args
            self.assertEqual(kwargs["repo"], repo)
            self.assertEqual(kwargs["repo_dir"], td)
            self.assertFalse(kwargs["interactive"])
            self.assertFalse(kwargs["allow_prompt"])

    def test_release_skips_publish_when_no_publish_flag_set(self) -> None:
        from pkgmgr.cli.commands.release import handle_release

        with tempfile.TemporaryDirectory() as td:
            repo = {"directory": td}

            args = SimpleNamespace(
                list=False,
                release_type="patch",
                message=None,
                preview=False,
                force=False,
                close=False,
                no_publish=True,
            )

            with (
                patch("pkgmgr.cli.commands.release.run_release") as m_release,
                patch("pkgmgr.cli.commands.release.run_publish") as m_publish,
            ):
                handle_release(args=args, ctx=self._ctx(), selected=[repo])

            m_release.assert_called_once()
            m_publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
