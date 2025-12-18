from __future__ import annotations

import unittest

from pkgmgr.actions.install.installers.nix.profile.result import extract_stdout_text


class TestExtractStdoutText(unittest.TestCase):
    def test_accepts_string(self) -> None:
        self.assertEqual(extract_stdout_text("hello"), "hello")

    def test_accepts_bytes(self) -> None:
        self.assertEqual(extract_stdout_text(b"hi"), "hi")

    def test_accepts_object_with_stdout_str(self) -> None:
        class R:
            stdout = "ok"

        self.assertEqual(extract_stdout_text(R()), "ok")

    def test_accepts_object_with_stdout_bytes(self) -> None:
        class R:
            stdout = b"ok"

        self.assertEqual(extract_stdout_text(R()), "ok")

    def test_fallback_str(self) -> None:
        class R:
            def __str__(self) -> str:
                return "repr"

        self.assertEqual(extract_stdout_text(R()), "repr")
