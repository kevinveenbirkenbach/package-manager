from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.actions.release.prompts import (
    confirm_proceed_release,
    should_delete_branch,
)


class TestShouldDeleteBranch(unittest.TestCase):
    def test_force_true_skips_prompt_and_returns_true(self) -> None:
        self.assertTrue(should_delete_branch(force=True))

    @patch("pkgmgr.actions.release.prompts.sys.stdin.isatty", return_value=False)
    def test_non_interactive_returns_false(self, _mock_isatty) -> None:
        self.assertFalse(should_delete_branch(force=False))

    @patch("pkgmgr.actions.release.prompts.sys.stdin.isatty", return_value=True)
    @patch("builtins.input", return_value="y")
    def test_interactive_yes_returns_true(self, _mock_input, _mock_isatty) -> None:
        self.assertTrue(should_delete_branch(force=False))

    @patch("pkgmgr.actions.release.prompts.sys.stdin.isatty", return_value=True)
    @patch("builtins.input", return_value="N")
    def test_interactive_no_returns_false(self, _mock_input, _mock_isatty) -> None:
        self.assertFalse(should_delete_branch(force=False))


class TestConfirmProceedRelease(unittest.TestCase):
    @patch("builtins.input", return_value="y")
    def test_confirm_yes(self, _mock_input) -> None:
        self.assertTrue(confirm_proceed_release())

    @patch("builtins.input", return_value="no")
    def test_confirm_no(self, _mock_input) -> None:
        self.assertFalse(confirm_proceed_release())

    @patch("builtins.input", side_effect=EOFError)
    def test_confirm_eof_returns_false(self, _mock_input) -> None:
        self.assertFalse(confirm_proceed_release())

    @patch("builtins.input", side_effect=KeyboardInterrupt)
    def test_confirm_keyboard_interrupt_returns_false(self, _mock_input) -> None:
        self.assertFalse(confirm_proceed_release())


if __name__ == "__main__":
    unittest.main()
