from __future__ import annotations

import unittest

from pkgmgr.actions.install.installers.nix.profile.normalizer import (
    coerce_index,
    normalize_elements,
)


class TestNormalizer(unittest.TestCase):
    def test_coerce_index_numeric_key(self) -> None:
        self.assertEqual(coerce_index("3", {"name": "x"}), 3)

    def test_coerce_index_explicit_field(self) -> None:
        self.assertEqual(coerce_index("pkgmgr-1", {"index": 7}), 7)
        self.assertEqual(coerce_index("pkgmgr-1", {"id": "8"}), 8)

    def test_coerce_index_trailing_number(self) -> None:
        self.assertEqual(coerce_index("pkgmgr-42", {"name": "x"}), 42)

    def test_normalize_elements_handles_missing_elements(self) -> None:
        self.assertEqual(normalize_elements({}), [])

    def test_normalize_elements_collects_store_paths(self) -> None:
        data = {
            "elements": {
                "pkgmgr-1": {
                    "name": "pkgmgr-1",
                    "attrPath": "packages.x86_64-linux.pkgmgr",
                    "storePaths": [
                        "/nix/store/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-pkgmgr"
                    ],
                },
                "2": {
                    "name": "foo",
                    "attrPath": "packages.x86_64-linux.default",
                    "storePath": "/nix/store/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb-foo",
                },
            }
        }
        entries = normalize_elements(data)
        self.assertEqual(len(entries), 2)
        self.assertTrue(entries[0].store_paths)
