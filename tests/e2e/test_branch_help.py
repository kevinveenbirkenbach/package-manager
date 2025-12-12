from __future__ import annotations

import io
import runpy
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr


def _run_pkgmgr_help(argv_tail: list[str]) -> str:
    """
    Run `pkgmgr <argv_tail> --help` via the main module and return captured output.

    argparse parses sys.argv[1:], so argv[0] must be a dummy program name.
    Any SystemExit with code 0 or None is treated as success.
    """
    original_argv = list(sys.argv)
    buffer = io.StringIO()
    cmd_repr = "pkgmgr " + " ".join(argv_tail) + " --help"

    try:
        # IMPORTANT: argv[0] must be a dummy program name
        sys.argv = ["pkgmgr"] + list(argv_tail) + ["--help"]

        try:
            with redirect_stdout(buffer), redirect_stderr(buffer):
                runpy.run_module("main", run_name="__main__")
        except SystemExit as exc:
            code = exc.code if isinstance(exc.code, int) else None
            if code not in (0, None):
                raise AssertionError(
                    f"{cmd_repr!r} failed with exit code {exc.code}."
                ) from exc

        return buffer.getvalue()
    finally:
        sys.argv = original_argv


class TestBranchHelpE2E(unittest.TestCase):
    """
    End-to-end tests ensuring that `pkgmgr branch` help commands
    run without error and print usage information.
    """

    def test_branch_root_help(self) -> None:
        """
        `pkgmgr branch --help` should run without error.
        """
        output = _run_pkgmgr_help(["branch"])
        self.assertIn("usage:", output)
        self.assertIn("pkgmgr branch", output)

    def test_branch_open_help(self) -> None:
        """
        `pkgmgr branch open --help` should run without error.
        """
        output = _run_pkgmgr_help(["branch", "open"])
        self.assertIn("usage:", output)
        self.assertIn("branch open", output)

    def test_branch_close_help(self) -> None:
        """
        `pkgmgr branch close --help` should run without error.
        """
        output = _run_pkgmgr_help(["branch", "close"])
        self.assertIn("usage:", output)
        self.assertIn("branch close", output)

    def test_branch_drop_help(self) -> None:
        """
        `pkgmgr branch drop --help` should run without error.
        """
        output = _run_pkgmgr_help(["branch", "drop"])
        self.assertIn("usage:", output)
        self.assertIn("branch drop", output)


if __name__ == "__main__":
    unittest.main()
