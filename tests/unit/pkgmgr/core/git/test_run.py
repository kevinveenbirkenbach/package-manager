import unittest
from unittest.mock import MagicMock, patch

from pkgmgr.core.git.errors import GitRunError
from pkgmgr.core.git.run import run


class TestGitRun(unittest.TestCase):
    def test_preview_mode_prints_and_does_not_execute(self) -> None:
        with (
            patch("pkgmgr.core.git.run.subprocess.run") as mock_run,
            patch("builtins.print") as mock_print,
        ):
            out = run(["status"], cwd="/tmp/repo", preview=True)

        self.assertEqual(out, "")
        mock_run.assert_not_called()
        mock_print.assert_called_once()
        printed = mock_print.call_args[0][0]
        self.assertIn("[PREVIEW] Would run in '/tmp/repo': git status", printed)

    def test_success_returns_stripped_stdout(self) -> None:
        completed = MagicMock()
        completed.stdout = " hello world \n"
        completed.stderr = ""
        completed.returncode = 0

        with patch(
            "pkgmgr.core.git.run.subprocess.run", return_value=completed
        ) as mock_run:
            out = run(["rev-parse", "HEAD"], cwd="/repo", preview=False)

        self.assertEqual(out, "hello world")

        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertEqual(args[0], ["git", "rev-parse", "HEAD"])
        self.assertEqual(kwargs["cwd"], "/repo")
        self.assertTrue(kwargs["check"])
        self.assertTrue(kwargs["text"])
        # ensure pipes are used (matches implementation intent)
        self.assertIsNotNone(kwargs["stdout"])
        self.assertIsNotNone(kwargs["stderr"])

    def test_failure_raises_giterror_with_details(self) -> None:
        # Build a CalledProcessError with stdout/stderr populated
        import subprocess as sp

        exc = sp.CalledProcessError(
            returncode=128,
            cmd=["git", "status"],
            output="OUT!",
            stderr="ERR!",
        )
        # Your implementation reads exc.stdout, but CalledProcessError stores it as .output
        # in some cases. Ensure .stdout exists for deterministic behavior.
        exc.stdout = "OUT!"
        exc.stderr = "ERR!"

        with patch("pkgmgr.core.git.run.subprocess.run", side_effect=exc):
            with self.assertRaises(GitRunError) as ctx:
                run(["status"], cwd="/bad/repo", preview=False)

        msg = str(ctx.exception)
        self.assertIn("Git command failed in '/bad/repo': git status", msg)
        self.assertIn("Exit code: 128", msg)
        self.assertIn("STDOUT:\nOUT!", msg)
        self.assertIn("STDERR:\nERR!", msg)


if __name__ == "__main__":
    unittest.main()
