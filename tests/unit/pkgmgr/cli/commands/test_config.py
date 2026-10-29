from __future__ import annotations

import types
import unittest
from unittest.mock import patch

from pkgmgr.cli.commands import config as config_cmd


class ConfigEditTests(unittest.TestCase):
    def _edit(self, path: str, returncode: int):
        with patch(
            "subprocess.Popen",
            side_effect=AssertionError("the editor's output must not be captured"),
        ), patch("subprocess.call", return_value=returncode) as call:
            config_cmd.handle_config(
                types.SimpleNamespace(subcommand="edit"),
                types.SimpleNamespace(user_config_path=path),
            )
        return call

    def test_nano_inherits_the_terminal(self):
        call = self._edit("/cfg/config.yaml", 0)

        call.assert_called_once_with(["nano", "/cfg/config.yaml"])

    def test_a_failing_editor_exits_with_its_code(self):
        with self.assertRaises(SystemExit) as raised:
            self._edit("/cfg/config.yaml", 3)

        self.assertEqual(raised.exception.code, 3)


if __name__ == "__main__":
    unittest.main()
