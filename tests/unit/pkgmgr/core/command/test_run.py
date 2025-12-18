import unittest
from unittest.mock import patch

import pkgmgr.core.command.run as run_mod


class TestRunCommand(unittest.TestCase):
    def test_preview_returns_success_without_running(self) -> None:
        with patch.object(run_mod.subprocess, "Popen") as popen_mock:
            result = run_mod.run_command("echo hi", cwd="/tmp", preview=True)
            self.assertEqual(result.returncode, 0)
            popen_mock.assert_not_called()

    def test_success_streams_and_returns_completed_process(self) -> None:
        cmd = [
            "python3",
            "-c",
            "print('out'); import sys; print('err', file=sys.stderr)",
        ]

        with patch.object(run_mod.sys, "exit") as exit_mock:
            result = run_mod.run_command(cmd, allow_failure=False)

        self.assertEqual(result.returncode, 0)
        self.assertIn("out", result.stdout)
        self.assertIn("err", result.stderr)
        exit_mock.assert_not_called()

    def test_failure_exits_when_not_allowed(self) -> None:
        cmd = [
            "python3",
            "-c",
            "import sys; print('oops', file=sys.stderr); sys.exit(2)",
        ]

        with patch.object(run_mod.sys, "exit", side_effect=SystemExit(2)) as exit_mock:
            with self.assertRaises(SystemExit) as ctx:
                run_mod.run_command(cmd, allow_failure=False)

        self.assertEqual(ctx.exception.code, 2)
        exit_mock.assert_called_once_with(2)

    def test_failure_does_not_exit_when_allowed(self) -> None:
        cmd = [
            "python3",
            "-c",
            "import sys; print('oops', file=sys.stderr); sys.exit(3)",
        ]

        with patch.object(run_mod.sys, "exit") as exit_mock:
            result = run_mod.run_command(cmd, allow_failure=True)

        self.assertEqual(result.returncode, 3)
        self.assertIn("oops", result.stderr)
        exit_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
