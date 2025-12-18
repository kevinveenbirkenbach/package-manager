from __future__ import annotations

import unittest

from pkgmgr.actions.install.installers.nix.profile_list import NixProfileListReader
from ._fakes import FakeRunResult, FakeRunner


class TestNixProfileListReader(unittest.TestCase):
    def test_entries_parses_indices_and_store_prefixes(self) -> None:
        out = """
          0  something  /nix/store/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-pkgmgr
          1  something  /nix/store/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb-foo
        """
        runner = FakeRunner(default=FakeRunResult(0, stdout=out))
        reader = NixProfileListReader(runner=runner)
        entries = reader.entries(ctx=None)
        self.assertEqual(entries[0][0], 0)
        self.assertTrue(entries[0][1].startswith("/nix/store/"))

    def test_indices_matching_store_prefixes(self) -> None:
        out = "  7  x  /nix/store/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-pkgmgr\n"
        runner = FakeRunner(default=FakeRunResult(0, stdout=out))
        reader = NixProfileListReader(runner=runner)
        hits = reader.indices_matching_store_prefixes(
            ctx=None,
            prefixes=["/nix/store/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-pkgmgr"],
        )
        self.assertEqual(hits, [7])
