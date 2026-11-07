from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.worktree import hooks


class TestHookCommand(unittest.TestCase):
    def _command(self, argv: list[str]) -> list[str]:
        return hooks.hook_command(hooks.INIT_HOOK, argv, "/worktree", 3)

    def test_bare_pin_runs_the_path_root_resolved_returned(self) -> None:
        with (
            patch.object(hooks, "trusted_path", return_value="/usr/bin"),
            patch.object(hooks.shutil, "which", return_value="/usr/bin/sh"),
            patch.object(hooks, "root_resolved", return_value="/usr/bin/dash"),
        ):
            self.assertEqual(
                self._command(["sh", "{path}", "{slot}"]),
                ["/usr/bin/dash", "/worktree", "3"],
            )

    def test_bare_pin_to_a_file_not_root_controlled_is_refused(self) -> None:
        with (
            patch.object(hooks, "trusted_path", return_value="/usr/bin"),
            patch.object(hooks.shutil, "which", return_value="/usr/bin/sh"),
            patch.object(hooks, "root_resolved", return_value=None),
            self.assertRaises(RuntimeError),
        ):
            self._command(["sh"])

    def test_relative_pin_with_a_slash_is_refused(self) -> None:
        with self.assertRaises(RuntimeError):
            self._command(["./init.sh"])

    def test_empty_pin_is_refused(self) -> None:
        with self.assertRaises(RuntimeError):
            self._command([])

    def test_absolute_pin_is_kept_verbatim(self) -> None:
        self.assertEqual(self._command(["/usr/bin/sh"]), ["/usr/bin/sh"])


if __name__ == "__main__":
    unittest.main()
