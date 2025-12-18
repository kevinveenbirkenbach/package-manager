from __future__ import annotations

import json
import unittest
from dataclasses import dataclass


@dataclass
class FakeRunResult:
    """
    Mimics your runner returning a structured result object.
    """

    returncode: int
    stdout: str
    stderr: str = ""


class FakeRunner:
    """
    Minimal runner stub: returns exactly what we configure.
    """

    def __init__(self, result):
        self._result = result

    def run(self, ctx, cmd: str, allow_failure: bool = False):
        return self._result


class TestE2ENixProfileListJsonParsing(unittest.TestCase):
    """
    This test verifies that NixProfileInspector can parse `nix profile list --json`
    regardless of whether the CommandRunner returns:
      - raw stdout string, OR
      - a RunResult-like object with a `.stdout` attribute.
    """

    def test_list_json_accepts_raw_string(self) -> None:
        from pkgmgr.actions.install.installers.nix.profile import NixProfileInspector

        payload = {
            "elements": {"pkgmgr-1": {"attrPath": "packages.x86_64-linux.pkgmgr"}}
        }
        raw = json.dumps(payload)

        runner = FakeRunner(raw)
        inspector = NixProfileInspector()

        data = inspector.list_json(ctx=None, runner=runner)
        self.assertEqual(
            data["elements"]["pkgmgr-1"]["attrPath"], "packages.x86_64-linux.pkgmgr"
        )

    def test_list_json_accepts_runresult_object(self) -> None:
        from pkgmgr.actions.install.installers.nix.profile import NixProfileInspector

        payload = {
            "elements": {"pkgmgr-1": {"attrPath": "packages.x86_64-linux.pkgmgr"}}
        }
        raw = json.dumps(payload)

        runner = FakeRunner(FakeRunResult(returncode=0, stdout=raw))
        inspector = NixProfileInspector()

        data = inspector.list_json(ctx=None, runner=runner)
        self.assertEqual(
            data["elements"]["pkgmgr-1"]["attrPath"], "packages.x86_64-linux.pkgmgr"
        )


if __name__ == "__main__":
    unittest.main()
