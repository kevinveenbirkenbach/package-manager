from __future__ import annotations

import os
import shutil
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pkgmgr.actions.worktree import trust

ROOT_DIR = 0o040755


class TestRootUids(unittest.TestCase):
    def _uids(
        self, uid_map: str, overflow: str | None = "65534\n", euid: int = 1000
    ) -> frozenset[int]:
        with tempfile.TemporaryDirectory() as tmp:
            mapping = os.path.join(tmp, "uid_map")
            overflow_file = os.path.join(tmp, "overflowuid")
            with open(mapping, "w") as fh:
                fh.write(uid_map)
            if overflow is not None:
                with open(overflow_file, "w") as fh:
                    fh.write(overflow)
            with (
                patch.object(trust, "UID_MAP", mapping),
                patch.object(trust, "OVERFLOW_UID", overflow_file),
                patch.object(trust.os, "geteuid", return_value=euid),
            ):
                return trust.root_uids()

    def test_initial_namespace_trusts_only_uid_0(self) -> None:
        self.assertEqual(self._uids("         0          0 4294967295\n"), {0})

    def test_namespace_without_uid_0_trusts_only_the_overflow_uid(self) -> None:
        self.assertEqual(self._uids("1000 1000 1\n"), {65534})

    def test_namespace_mapping_uid_0_to_a_user_trusts_only_the_overflow_uid(
        self,
    ) -> None:
        self.assertEqual(self._uids("0 1000 1\n"), {65534})

    def test_nested_namespace_mapping_a_user_to_parent_0_trusts_only_overflow(
        self,
    ) -> None:
        self.assertEqual(self._uids("1000 0 1\n"), {65534})

    def test_own_uid_unmapped_trusts_no_uid(self) -> None:
        self.assertEqual(self._uids("", euid=65534), frozenset())

    def test_unreadable_map_trusts_no_uid(self) -> None:
        with patch.object(trust, "UID_MAP", "/nonexistent/uid_map"):
            self.assertEqual(trust.root_uids(), frozenset())

    def test_unreadable_overflow_uid_trusts_no_uid(self) -> None:
        self.assertEqual(self._uids("1000 1000 1\n", overflow=None), frozenset())

    def test_malformed_map_trusts_no_uid(self) -> None:
        self.assertEqual(self._uids("0 zero 1\n"), frozenset())


class TestRootResolved(unittest.TestCase):
    PATH = "/usr/bin/tool"

    def _resolve(
        self,
        stats: dict[str, tuple[int, int]],
        owners: frozenset[int] = frozenset({0}),
        nosuid: frozenset[str] = frozenset(),
    ) -> str | None:
        def fake_stat(path: str) -> SimpleNamespace:
            if path not in stats:
                raise FileNotFoundError(path)
            uid, mode = stats[path]
            return SimpleNamespace(st_uid=uid, st_mode=mode)

        def fake_statvfs(path: str) -> SimpleNamespace:
            return SimpleNamespace(f_flag=os.ST_NOSUID if path in nosuid else 0)

        with (
            patch.object(trust, "root_uids", return_value=owners),
            patch.object(trust.os.path, "realpath", side_effect=lambda p: p),
            patch.object(trust.os, "stat", side_effect=fake_stat),
            patch.object(trust.os, "statvfs", side_effect=fake_statvfs),
        ):
            return trust.root_resolved(self.PATH)

    def _tree(self) -> dict[str, tuple[int, int]]:
        return {
            "/": (0, ROOT_DIR),
            "/usr": (0, ROOT_DIR),
            "/usr/bin": (0, ROOT_DIR),
            self.PATH: (0, 0o100755),
        }

    def test_root_owned_chain_returns_the_resolved_path(self) -> None:
        self.assertEqual(self._resolve(self._tree()), self.PATH)

    def test_non_root_ancestor_is_refused(self) -> None:
        stats = self._tree()
        stats["/usr"] = (1000, ROOT_DIR)
        self.assertIsNone(self._resolve(stats))

    def test_group_writable_leaf_is_refused(self) -> None:
        stats = self._tree()
        stats[self.PATH] = (0, 0o100775)
        self.assertIsNone(self._resolve(stats))

    def test_other_writable_ancestor_is_refused(self) -> None:
        stats = self._tree()
        stats["/usr/bin"] = (0, 0o040757)
        self.assertIsNone(self._resolve(stats))

    def test_stat_error_is_refused(self) -> None:
        stats = self._tree()
        del stats["/usr"]
        self.assertIsNone(self._resolve(stats))

    def test_nosuid_component_is_refused_in_the_initial_namespace(self) -> None:
        self.assertIsNone(self._resolve(self._tree(), nosuid=frozenset({"/usr"})))

    def test_nosuid_is_ignored_inside_another_namespace(self) -> None:
        stats = {path: (65534, mode) for path, (_, mode) in self._tree().items()}
        everything = frozenset(stats)
        self.assertEqual(
            self._resolve(stats, owners=frozenset({65534}), nosuid=everything),
            self.PATH,
        )


class TestTrustedPath(unittest.TestCase):
    def test_symlinked_entry_is_kept_only_resolved(self) -> None:
        system = os.path.dirname(os.path.realpath(shutil.which("true")))
        with tempfile.TemporaryDirectory() as tmp:
            link = os.path.join(tmp, "bin")
            os.symlink(system, link)
            with patch.dict(os.environ, {"PATH": link}):
                self.assertEqual(trust.trusted_path(), system)

    def test_entry_keeps_the_resolution_it_was_checked_under(self) -> None:
        system = os.path.dirname(os.path.realpath(shutil.which("true")))
        with tempfile.TemporaryDirectory() as tmp:
            link = os.path.join(tmp, "bin")
            os.symlink(system, link)
            with (
                patch.dict(os.environ, {"PATH": link}),
                patch.object(trust.os.path, "realpath", side_effect=[system, tmp]),
            ):
                self.assertEqual(trust.trusted_path(), system)

    def test_no_root_controlled_entry_is_refused(self) -> None:
        with (
            patch.object(trust, "root_resolved", return_value=None),
            self.assertRaises(RuntimeError),
        ):
            trust.trusted_path()


if __name__ == "__main__":
    unittest.main()
