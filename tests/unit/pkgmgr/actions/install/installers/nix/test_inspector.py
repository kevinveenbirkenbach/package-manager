from __future__ import annotations

import json
import unittest

from pkgmgr.actions.install.installers.nix.profile import NixProfileInspector
from ._fakes import FakeRunResult, FakeRunner


class TestNixProfileInspector(unittest.TestCase):
    def test_list_json_accepts_raw_string(self) -> None:
        payload = {"elements": {"pkgmgr-1": {"attrPath": "packages.x86_64-linux.pkgmgr"}}}
        raw = json.dumps(payload)
        runner = FakeRunner(default=raw)
        insp = NixProfileInspector()
        data = insp.list_json(ctx=None, runner=runner)
        self.assertEqual(data["elements"]["pkgmgr-1"]["attrPath"], "packages.x86_64-linux.pkgmgr")

    def test_list_json_accepts_result_object(self) -> None:
        payload = {"elements": {"pkgmgr-1": {"attrPath": "packages.x86_64-linux.pkgmgr"}}}
        raw = json.dumps(payload)
        runner = FakeRunner(default=FakeRunResult(0, stdout=raw))
        insp = NixProfileInspector()
        data = insp.list_json(ctx=None, runner=runner)
        self.assertEqual(data["elements"]["pkgmgr-1"]["attrPath"], "packages.x86_64-linux.pkgmgr")

    def test_find_remove_tokens_for_output_includes_output_first(self) -> None:
        payload = {
            "elements": {
                "pkgmgr-1": {"name": "pkgmgr-1", "attrPath": "packages.x86_64-linux.pkgmgr"},
                "default-1": {"name": "default-1", "attrPath": "packages.x86_64-linux.default"},
            }
        }
        raw = json.dumps(payload)
        runner = FakeRunner(default=FakeRunResult(0, stdout=raw))
        insp = NixProfileInspector()
        tokens = insp.find_remove_tokens_for_output(ctx=None, runner=runner, output="pkgmgr")
        self.assertEqual(tokens[0], "pkgmgr")
        self.assertIn("pkgmgr-1", tokens)

    def test_find_remove_tokens_for_store_prefixes(self) -> None:
        payload = {
            "elements": {
                "pkgmgr-1": {
                    "name": "pkgmgr-1",
                    "attrPath": "packages.x86_64-linux.pkgmgr",
                    "storePaths": ["/nix/store/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-pkgmgr"],
                },
                "something": {
                    "name": "other",
                    "attrPath": "packages.x86_64-linux.other",
                    "storePaths": ["/nix/store/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb-other"],
                },
            }
        }
        raw = json.dumps(payload)
        runner = FakeRunner(default=FakeRunResult(0, stdout=raw))
        insp = NixProfileInspector()
        tokens = insp.find_remove_tokens_for_store_prefixes(
            ctx=None, runner=runner, prefixes=["/nix/store/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-pkgmgr"]
        )
        self.assertIn("pkgmgr-1", tokens)
