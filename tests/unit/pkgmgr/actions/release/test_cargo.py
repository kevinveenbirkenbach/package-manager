from __future__ import annotations

import os
import tempfile
import unittest

from pkgmgr.actions.release.files import update_cargo_version

CARGO_TOML = """[package]
name = "security-check"
version = "0.1.0"
edition = "2024"

[dependencies]
serde = { version = "1.0.0" }
"""

CARGO_LOCK = """version = 4

[[package]]
name = "security-check"
version = "0.1.0"
source = "registry+https://github.com/rust-lang/crates.io-index"
checksum = "abc"

[[package]]
name = "security-check"
version = "0.1.0"
dependencies = [
 "serde",
]

[[package]]
name = "serde"
version = "0.1.0"
source = "registry+https://github.com/rust-lang/crates.io-index"
"""


class TestUpdateCargoVersion(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, name: str, content: str) -> str:
        path = os.path.join(self.root, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def _read(self, name: str) -> str:
        with open(os.path.join(self.root, name), encoding="utf-8") as f:
            return f.read()

    def test_bumps_package_and_local_lock_entry_only(self) -> None:
        toml = self._write("Cargo.toml", CARGO_TOML)
        lock = self._write("Cargo.lock", CARGO_LOCK)

        changed = update_cargo_version(self.root, "0.4.0")

        self.assertEqual(changed, [toml, lock])
        self.assertEqual(
            self._read("Cargo.toml"),
            CARGO_TOML.replace('version = "0.1.0"', 'version = "0.4.0"'),
        )
        self.assertEqual(
            self._read("Cargo.lock"),
            CARGO_LOCK.replace(
                'name = "security-check"\nversion = "0.1.0"\ndependencies',
                'name = "security-check"\nversion = "0.4.0"\ndependencies',
            ),
        )

    def test_without_cargo_toml_changes_nothing(self) -> None:
        self.assertEqual(update_cargo_version(self.root, "0.4.0"), [])
        self.assertEqual(os.listdir(self.root), [])

    def test_workspace_without_package_is_untouched(self) -> None:
        workspace = '[workspace]\nmembers = ["a"]\n'
        self._write("Cargo.toml", workspace)

        self.assertEqual(update_cargo_version(self.root, "0.4.0"), [])
        self.assertEqual(self._read("Cargo.toml"), workspace)

    def test_without_lock_bumps_only_toml(self) -> None:
        toml = self._write("Cargo.toml", CARGO_TOML)

        self.assertEqual(update_cargo_version(self.root, "0.4.0"), [toml])

    def test_preview_writes_nothing(self) -> None:
        self._write("Cargo.toml", CARGO_TOML)
        self._write("Cargo.lock", CARGO_LOCK)

        update_cargo_version(self.root, "0.4.0", preview=True)

        self.assertEqual(self._read("Cargo.toml"), CARGO_TOML)
        self.assertEqual(self._read("Cargo.lock"), CARGO_LOCK)

    def test_lock_without_local_entry_fails_before_writing(self) -> None:
        self._write("Cargo.toml", CARGO_TOML)
        self._write("Cargo.lock", 'version = 4\n\n[[package]]\nname = "serde"\n')

        with self.assertRaises(RuntimeError):
            update_cargo_version(self.root, "0.4.0")
        self.assertEqual(self._read("Cargo.toml"), CARGO_TOML)


if __name__ == "__main__":
    unittest.main()
