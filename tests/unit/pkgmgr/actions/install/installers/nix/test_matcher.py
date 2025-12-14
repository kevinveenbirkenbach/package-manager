from __future__ import annotations

import unittest

from pkgmgr.actions.install.installers.nix.profile.models import NixProfileEntry
from pkgmgr.actions.install.installers.nix.profile.matcher import entry_matches_output, entry_matches_store_path


class TestMatcher(unittest.TestCase):
    def _e(self, name: str, attr: str) -> NixProfileEntry:
        return NixProfileEntry(
            key="pkgmgr-1",
            index=None,
            name=name,
            attr_path=attr,
            store_paths=["/nix/store/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-pkgmgr"],
        )

    def test_matches_direct_name(self) -> None:
        self.assertTrue(entry_matches_output(self._e("pkgmgr", ""), "pkgmgr"))

    def test_matches_attrpath_hash(self) -> None:
        self.assertTrue(entry_matches_output(self._e("", "github:me/repo#pkgmgr"), "pkgmgr"))

    def test_matches_attrpath_dot_suffix(self) -> None:
        self.assertTrue(entry_matches_output(self._e("", "packages.x86_64-linux.pkgmgr"), "pkgmgr"))

    def test_matches_name_with_suffix_number(self) -> None:
        self.assertTrue(entry_matches_output(self._e("pkgmgr-1", ""), "pkgmgr"))

    def test_package_manager_special_case(self) -> None:
        self.assertTrue(entry_matches_output(self._e("package-manager-2", ""), "pkgmgr"))

    def test_store_path_match(self) -> None:
        entry = self._e("pkgmgr-1", "")
        self.assertTrue(entry_matches_store_path(entry, "/nix/store/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-pkgmgr"))
        self.assertFalse(entry_matches_store_path(entry, "/nix/store/cccccccccccccccccccccccccccccccc-zzz"))
