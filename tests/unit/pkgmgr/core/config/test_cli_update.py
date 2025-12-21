from __future__ import annotations

import io
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from pkgmgr.cli.commands import config as config_cmd


class FindDefaultsSourceDirTests(unittest.TestCase):
    def test_prefers_pkg_root_config_over_project_root_config(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pkg_root = root / "site-packages" / "pkgmgr"
            pkg_root.mkdir(parents=True)

            # both exist
            (pkg_root / "config").mkdir(parents=True)
            (pkg_root.parent / "config").mkdir(parents=True)

            fake_pkgmgr = types.SimpleNamespace(__file__=str(pkg_root / "__init__.py"))
            with patch.dict(sys.modules, {"pkgmgr": fake_pkgmgr}):
                found = config_cmd._find_defaults_source_dir()

            self.assertEqual(Path(found).resolve(), (pkg_root / "config").resolve())

    def test_falls_back_to_project_root_config(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pkg_root = root / "site-packages" / "pkgmgr"
            pkg_root.mkdir(parents=True)

            # only project_root config exists
            (pkg_root.parent / "config").mkdir(parents=True)

            fake_pkgmgr = types.SimpleNamespace(__file__=str(pkg_root / "__init__.py"))
            with patch.dict(sys.modules, {"pkgmgr": fake_pkgmgr}):
                found = config_cmd._find_defaults_source_dir()

            self.assertEqual(
                Path(found).resolve(), (pkg_root.parent / "config").resolve()
            )

    def test_returns_none_when_no_config_dirs_exist(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pkg_root = root / "site-packages" / "pkgmgr"
            pkg_root.mkdir(parents=True)

            fake_pkgmgr = types.SimpleNamespace(__file__=str(pkg_root / "__init__.py"))
            with patch.dict(sys.modules, {"pkgmgr": fake_pkgmgr}):
                found = config_cmd._find_defaults_source_dir()

            self.assertIsNone(found)


class UpdateDefaultConfigsTests(unittest.TestCase):
    def test_copies_yaml_files_skips_config_yaml(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_dir = root / "src"
            source_dir.mkdir()

            # Create files
            (source_dir / "a.yaml").write_text("x: 1\n", encoding="utf-8")
            (source_dir / "b.yml").write_text("y: 2\n", encoding="utf-8")
            (source_dir / "config.yaml").write_text(
                "should_not_copy: true\n", encoding="utf-8"
            )
            (source_dir / "notes.txt").write_text("nope\n", encoding="utf-8")

            home = root / "home"
            dest_cfg_dir = home / ".config" / "pkgmgr"
            dest_cfg_dir.mkdir(parents=True)
            user_config_path = str(dest_cfg_dir / "config.yaml")

            # Patch the source dir finder to our temp source_dir
            with patch.object(
                config_cmd, "_find_defaults_source_dir", return_value=str(source_dir)
            ):
                with patch.dict(os.environ, {"HOME": str(home)}):
                    config_cmd._update_default_configs(user_config_path)

            self.assertTrue((dest_cfg_dir / "a.yaml").is_file())
            self.assertTrue((dest_cfg_dir / "b.yml").is_file())
            self.assertFalse(
                (dest_cfg_dir / "config.yaml")
                .read_text(encoding="utf-8")
                .startswith("should_not_copy")
            )

            # Ensure config.yaml was not overwritten (it may exist, but should remain original if we create it)
            # We'll strengthen: create an original config.yaml then re-run
            (dest_cfg_dir / "config.yaml").write_text(
                "original: true\n", encoding="utf-8"
            )

            with patch.object(
                config_cmd, "_find_defaults_source_dir", return_value=str(source_dir)
            ):
                with patch.dict(os.environ, {"HOME": str(home)}):
                    config_cmd._update_default_configs(user_config_path)

            self.assertEqual(
                (dest_cfg_dir / "config.yaml").read_text(encoding="utf-8"),
                "original: true\n",
            )

    def test_prints_warning_and_returns_when_no_source_dir(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            home = root / "home"
            dest_cfg_dir = home / ".config" / "pkgmgr"
            dest_cfg_dir.mkdir(parents=True)
            user_config_path = str(dest_cfg_dir / "config.yaml")

            buf = io.StringIO()
            with patch.object(
                config_cmd, "_find_defaults_source_dir", return_value=None
            ):
                with patch("sys.stdout", buf):
                    with patch.dict(os.environ, {"HOME": str(home)}):
                        config_cmd._update_default_configs(user_config_path)

            out = buf.getvalue()
            self.assertIn("[WARN] No config directory found", out)


if __name__ == "__main__":
    unittest.main()
