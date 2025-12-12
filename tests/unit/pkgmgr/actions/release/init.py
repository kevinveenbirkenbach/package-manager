from __future__ import annotations

import unittest


class TestReleasePackageInit(unittest.TestCase):
    def test_release_is_reexported(self) -> None:
        from pkgmgr.actions.release import release  # noqa: F401

        self.assertTrue(callable(release))


if __name__ == "__main__":
    unittest.main()
