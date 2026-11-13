from __future__ import annotations

import os
import pwd
import unittest
from unittest.mock import MagicMock, patch

from pkgmgr.core.git.errors import GitRunError
from pkgmgr.core.git.run import CALLER_CONFIG, DEFAULT_CONFIG, run, strict_env


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
        self.assertTrue(kwargs["capture_output"])

    def test_scan_input_text_replaces_closed_stdin(self) -> None:
        completed = MagicMock()
        completed.stdout = "abc\n"

        with patch(
            "pkgmgr.core.git.run.subprocess.run", return_value=completed
        ) as mock_run:
            out = run(["cat-file", "--batch-check"], scan=True, input_text="x\n")

        self.assertEqual(out, "abc")
        kwargs = mock_run.call_args.kwargs
        self.assertEqual(kwargs["input"], "x\n")
        self.assertNotIn("stdin", kwargs)
        self.assertIn("timeout", kwargs)

    OVERRIDES = (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_COMMON_DIR",
        "GIT_CONFIG",
        "GIT_CEILING_DIRECTORIES",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_SYSTEM",
        "GIT_CONFIG_PARAMETERS",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_KEY_0",
        "GIT_CONFIG_VALUE_0",
        "GIT_CONFIG_KEY_X",
    )
    CONFIG_READ = (
        "GIT_CEILING_DIRECTORIES",
        "GIT_CONFIG_COUNT",
        "GIT_CONFIG_GLOBAL",
        "GIT_CONFIG_KEY_0",
        "GIT_CONFIG_PARAMETERS",
        "GIT_CONFIG_SYSTEM",
        "GIT_CONFIG_VALUE_0",
    )

    def _env(
        self, scan: bool, strict: bool, view: str | None = None
    ) -> dict[str, str] | None:
        completed = MagicMock()
        completed.stdout = ""
        planted = {
            **dict.fromkeys(self.OVERRIDES, "/elsewhere"),
            "HOME": "/elsewhere",
            "XDG_CONFIG_HOME": "/elsewhere",
        }
        with (
            patch.dict("os.environ", planted),
            patch(
                "pkgmgr.core.git.run.subprocess.run", return_value=completed
            ) as mock_run,
        ):
            if strict:
                with strict_env():
                    run(["status"], scan=scan, config_view=view)
            else:
                run(["status"], scan=scan, config_view=view)
        return mock_run.call_args.kwargs.get("env")

    def _kept(self, env: dict[str, str]) -> list[str]:
        return sorted(name for name in self.OVERRIDES if name in env)

    def test_scan_drops_repository_overrides_from_the_environment(self) -> None:
        unset = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")
        for view in (None, CALLER_CONFIG):
            with self.subTest(view=view):
                env = self._env(scan=True, strict=False, view=view)

                self.assertEqual(
                    self._kept(env),
                    sorted(name for name in self.OVERRIDES if name not in unset),
                )
                self.assertEqual(env.get("GIT_CONFIG_NOSYSTEM"), None if view else "1")
                self.assertIsNone(self._env(scan=False, strict=False, view=view))

    def test_strict_env_keeps_only_the_ceiling(self) -> None:
        for scan in (True, False):
            with self.subTest(scan=scan):
                env = self._env(scan=scan, strict=True)

                self.assertEqual(self._kept(env), ["GIT_CEILING_DIRECTORIES"])
                self.assertEqual(env.get("GIT_CONFIG_NOSYSTEM"), "1")

    def test_strict_caller_config_also_keeps_the_config_variables(self) -> None:
        for scan in (True, False):
            with self.subTest(scan=scan):
                env = self._env(scan=scan, strict=True, view=CALLER_CONFIG)

                self.assertEqual(self._kept(env), list(self.CONFIG_READ))
                self.assertIsNone(env.get("GIT_CONFIG_NOSYSTEM"))
                self.assertEqual(env.get("HOME"), "/elsewhere")

    def test_default_config_ignores_the_environment(self) -> None:
        home = pwd.getpwuid(os.getuid()).pw_dir
        for strict in (True, False):
            with self.subTest(strict=strict):
                env = self._env(scan=True, strict=strict, view=DEFAULT_CONFIG)

                self.assertEqual(self._kept(env), ["GIT_CEILING_DIRECTORIES"])
                self.assertIsNone(env.get("GIT_CONFIG_NOSYSTEM"))
                self.assertEqual(env.get("HOME"), home)
                self.assertFalse("XDG_CONFIG_HOME" in env)

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

        with (
            patch("pkgmgr.core.git.run.subprocess.run", side_effect=exc),
            self.assertRaises(GitRunError) as ctx,
        ):
            run(["status"], cwd="/bad/repo", preview=False)

        msg = str(ctx.exception)
        self.assertIn("Git command failed in '/bad/repo': git status", msg)
        self.assertIn("Exit code: 128", msg)
        self.assertIn("STDOUT:\nOUT!", msg)
        self.assertIn("STDERR:\nERR!", msg)


if __name__ == "__main__":
    unittest.main()
