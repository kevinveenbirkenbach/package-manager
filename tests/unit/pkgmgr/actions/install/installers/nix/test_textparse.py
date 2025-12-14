from __future__ import annotations

import unittest

from pkgmgr.actions.install.installers.nix.textparse import NixConflictTextParser


class TestNixConflictTextParser(unittest.TestCase):
    def test_remove_tokens_parses_unquoted_and_quoted(self) -> None:
        t = NixConflictTextParser()
        text = '''
        nix profile remove pkgmgr
        nix profile remove 'pkgmgr-1'
        nix profile remove "default-2"
        '''
        tokens = t.remove_tokens(text)
        self.assertEqual(tokens, ["pkgmgr", "pkgmgr-1", "default-2"])

    def test_existing_store_prefixes_extracts_existing_section_only(self) -> None:
        t = NixConflictTextParser()
        text = '''
        error: An existing package already provides the following file:
          /nix/store/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-pkgmgr/bin/pkgmgr
          /nix/store/bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb-pkgmgr/share/doc
        This is the conflicting file from the new package:
          /nix/store/cccccccccccccccccccccccccccccccc-pkgmgr/bin/pkgmgr
        '''
        prefixes = t.existing_store_prefixes(text)
        self.assertEqual(len(prefixes), 2)
        self.assertTrue(prefixes[0].startswith("/nix/store/"))
