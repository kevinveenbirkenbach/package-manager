from __future__ import annotations

import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch


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

            with patch("pkgmgr.cli.commands.release.run_release") as m_release, patch(
                "pkgmgr.cli.commands.release.run_publish"
            ) as m_publish, patch(
                "pkgmgr.cli.commands.release.sys.stdin.isatty", return_value=False
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

            with patch("pkgmgr.cli.commands.release.run_release") as m_release, patch(
                "pkgmgr.cli.commands.release.run_publish"
            ) as m_publish:
                handle_release(args=args, ctx=self._ctx(), selected=selected)

            m_release.assert_called_once()
            m_publish.assert_not_called()


if __name__ == "__main__":
    unittest.main()
