from __future__ import annotations

import json
import unittest

from pkgmgr.actions.install.installers.nix.profile.parser import parse_profile_list_json


class TestParseProfileListJson(unittest.TestCase):
    def test_parses_valid_json(self) -> None:
        payload = {"elements": {"0": {"name": "pkgmgr"}}}
        raw = json.dumps(payload)
        self.assertEqual(parse_profile_list_json(raw)["elements"]["0"]["name"], "pkgmgr")

    def test_raises_systemexit_on_invalid_json(self) -> None:
        with self.assertRaises(SystemExit) as cm:
            parse_profile_list_json("{not json")
        self.assertIn("Failed to parse", str(cm.exception))
