from __future__ import annotations

import os
import runpy
import sys
import unittest


PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..")
)


class TestIntegrationReleaseCommand(unittest.TestCase):
    def _run_pkgmgr(
        self,
        argv: list[str],
        expect_success: bool,
    ) -> None:
        """
        Run the main entry point with the given argv and assert on success/failure.

        argv must include the program name as argv[0], e.g. "":
            ["", "release", "patch", "pkgmgr", "--preview"]
        """
        cmd_repr = " ".join(argv[1:])
        original_argv = list(sys.argv)

        try:
            sys.argv = argv
            try:
                # Execute main.py as if called via `python main.py ...`
                runpy.run_module("main", run_name="__main__")
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 1
                if expect_success and code != 0:
                    print()
                    print(f"[TEST] Command   : {cmd_repr}")
                    print(f"[TEST] Exit code : {code}")
                    raise AssertionError(
                        f"{cmd_repr!r} failed with exit code {code}. "
                        "Scroll up to inspect the output printed before failure."
                    ) from exc
                if not expect_success and code == 0:
                    print()
                    print(f"[TEST] Command   : {cmd_repr}")
                    print(f"[TEST] Exit code : {code}")
                    raise AssertionError(
                        f"{cmd_repr!r} unexpectedly succeeded with exit code 0."
                    ) from exc
            else:
                # No SystemExit: treat as success when expect_success is True,
                # otherwise as a failure (we expected a non-zero exit).
                if not expect_success:
                    raise AssertionError(
                        f"{cmd_repr!r} returned normally (expected non-zero exit)."
                    )
        finally:
            sys.argv = original_argv

    def test_release_for_unknown_repo_fails_cleanly(self) -> None:
        """
        Releasing a non-existent repository identifier must fail
        with a non-zero exit code, but without crashing the interpreter.
        """
        argv = [
            "",
            "release",
            "patch",
            "does-not-exist-xyz",
        ]
        self._run_pkgmgr(argv, expect_success=False)

    def test_release_preview_for_pkgmgr_repository(self) -> None:
        """
        Sanity-check the happy path for the CLI:

        - Runs `pkgmgr release patch pkgmgr --preview`
        - Must exit with code 0
        - Uses the real configuration + repository selection
        - Exercises the new --preview mode end-to-end.
        """
        argv = [
            "",
            "release",
            "patch",
            "pkgmgr",
            "--preview",
        ]

        original_cwd = os.getcwd()
        try:
            os.chdir(PROJECT_ROOT)
            self._run_pkgmgr(argv, expect_success=True)
        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
