from __future__ import annotations

import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from pkgmgr.core.config.load import (
    _deep_merge,
    _merge_repo_lists,
    _load_layer_dir,
    _load_defaults_from_package_or_project,
    load_config,
)


class DeepMergeTests(unittest.TestCase):
    def test_deep_merge_overrides_scalars_and_merges_dicts(self):
        base = {"a": 1, "b": {"x": 1, "y": 2}, "c": {"k": 1}}
        override = {"a": 2, "b": {"y": 99, "z": 3}, "c": 7}
        merged = _deep_merge(base, override)

        self.assertEqual(merged["a"], 2)
        self.assertEqual(merged["b"]["x"], 1)
        self.assertEqual(merged["b"]["y"], 99)
        self.assertEqual(merged["b"]["z"], 3)
        self.assertEqual(merged["c"], 7)


class MergeRepoListsTests(unittest.TestCase):
    def test_merge_repo_lists_adds_new_repo_and_tracks_category(self):
        base = []
        new = [{"provider": "github", "account": "a", "repository": "r", "x": 1}]
        _merge_repo_lists(base, new, category_name="cat1")

        self.assertEqual(len(base), 1)
        self.assertEqual(base[0]["provider"], "github")
        self.assertEqual(base[0]["x"], 1)
        self.assertIn("category_files", base[0])
        self.assertIn("cat1", base[0]["category_files"])

    def test_merge_repo_lists_merges_existing_repo_fields(self):
        base = [
            {
                "provider": "github",
                "account": "a",
                "repository": "r",
                "x": 1,
                "d": {"a": 1},
            }
        ]
        new = [
            {
                "provider": "github",
                "account": "a",
                "repository": "r",
                "x": 2,
                "d": {"b": 2},
            }
        ]
        _merge_repo_lists(base, new, category_name="cat2")

        self.assertEqual(len(base), 1)
        self.assertEqual(base[0]["x"], 2)
        self.assertEqual(base[0]["d"]["a"], 1)
        self.assertEqual(base[0]["d"]["b"], 2)
        self.assertIn("cat2", base[0]["category_files"])

    def test_merge_repo_lists_incomplete_key_appends(self):
        base = []
        new = [{"foo": "bar"}]  # no provider/account/repository
        _merge_repo_lists(base, new, category_name="cat")

        self.assertEqual(len(base), 1)
        self.assertEqual(base[0]["foo"], "bar")
        self.assertIn("cat", base[0].get("category_files", []))


class LoadLayerDirTests(unittest.TestCase):
    def test_load_layer_dir_merges_directories_and_repos_across_files_sorted(self):
        with tempfile.TemporaryDirectory() as td:
            cfg_dir = Path(td)

            # 10_b.yaml should be applied after 01_a.yaml due to name sorting
            (cfg_dir / "01_a.yaml").write_text(
                yaml.safe_dump(
                    {
                        "directories": {"repositories": "/opt/Repos"},
                        "repositories": [
                            {
                                "provider": "github",
                                "account": "a",
                                "repository": "r1",
                                "x": 1,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (cfg_dir / "10_b.yaml").write_text(
                yaml.safe_dump(
                    {
                        "directories": {"binaries": "/usr/local/bin"},
                        "repositories": [
                            {
                                "provider": "github",
                                "account": "a",
                                "repository": "r1",
                                "x": 2,
                            },
                            {"provider": "github", "account": "a", "repository": "r2"},
                        ],
                    }
                ),
                encoding="utf-8",
            )

            defaults = _load_layer_dir(cfg_dir, skip_filename="config.yaml")

            self.assertEqual(defaults["directories"]["repositories"], "/opt/Repos")
            self.assertEqual(defaults["directories"]["binaries"], "/usr/local/bin")

            # r1 merged: x becomes 2 and has category_files including both stems
            repos = defaults["repositories"]
            self.assertEqual(len(repos), 2)
            r1 = next(r for r in repos if r["repository"] == "r1")
            self.assertEqual(r1["x"], 2)
            self.assertIn("01_a", r1.get("category_files", []))
            self.assertIn("10_b", r1.get("category_files", []))

    def test_load_layer_dir_skips_config_yaml(self):
        with tempfile.TemporaryDirectory() as td:
            cfg_dir = Path(td)
            (cfg_dir / "config.yaml").write_text(
                yaml.safe_dump({"directories": {"x": 1}}), encoding="utf-8"
            )
            (cfg_dir / "defaults.yaml").write_text(
                yaml.safe_dump({"directories": {"x": 2}}), encoding="utf-8"
            )

            defaults = _load_layer_dir(cfg_dir, skip_filename="config.yaml")
            # only defaults.yaml should apply
            self.assertEqual(defaults["directories"]["x"], 2)


class DefaultsFromPackageOrProjectTests(unittest.TestCase):
    def test_defaults_from_pkg_root_config_wins(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            pkg_root = root / "site-packages" / "pkgmgr"
            cfg_dir = pkg_root / "config"
            cfg_dir.mkdir(parents=True)

            (cfg_dir / "defaults.yaml").write_text(
                yaml.safe_dump(
                    {"directories": {"repositories": "/opt/Repos"}, "repositories": []}
                ),
                encoding="utf-8",
            )

            fake_pkgmgr = types.SimpleNamespace(__file__=str(pkg_root / "__init__.py"))
            with patch.dict(sys.modules, {"pkgmgr": fake_pkgmgr}):
                defaults = _load_defaults_from_package_or_project()

            self.assertEqual(defaults["directories"]["repositories"], "/opt/Repos")

    def test_defaults_from_repo_root_src_layout(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            pkg_root = repo_root / "src" / "pkgmgr"
            cfg_dir = repo_root / "config"
            cfg_dir.mkdir(parents=True)
            pkg_root.mkdir(parents=True)

            (cfg_dir / "defaults.yaml").write_text(
                yaml.safe_dump(
                    {"directories": {"binaries": "/usr/local/bin"}, "repositories": []}
                ),
                encoding="utf-8",
            )

            fake_pkgmgr = types.SimpleNamespace(__file__=str(pkg_root / "__init__.py"))
            with patch.dict(sys.modules, {"pkgmgr": fake_pkgmgr}):
                defaults = _load_defaults_from_package_or_project()

            self.assertEqual(defaults["directories"]["binaries"], "/usr/local/bin")

    def test_defaults_returns_empty_when_no_config_found(self):
        with tempfile.TemporaryDirectory() as td:
            pkg_root = Path(td) / "site-packages" / "pkgmgr"
            pkg_root.mkdir(parents=True)
            fake_pkgmgr = types.SimpleNamespace(__file__=str(pkg_root / "__init__.py"))

            with patch.dict(sys.modules, {"pkgmgr": fake_pkgmgr}):
                defaults = _load_defaults_from_package_or_project()

            self.assertEqual(defaults, {"directories": {}, "repositories": []})


class LoadConfigIntegrationUnitTests(unittest.TestCase):
    def test_load_config_prefers_user_dir_defaults_over_package_defaults(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "home"
            user_cfg_dir = home / ".config" / "pkgmgr"
            user_cfg_dir.mkdir(parents=True)
            user_config_path = str(user_cfg_dir / "config.yaml")

            # user dir defaults exist -> should be used, package fallback must not matter
            (user_cfg_dir / "aa.yaml").write_text(
                yaml.safe_dump({"directories": {"repositories": "/USER/Repos"}}),
                encoding="utf-8",
            )
            (user_cfg_dir / "config.yaml").write_text(
                yaml.safe_dump({"directories": {"binaries": "/USER/bin"}}),
                encoding="utf-8",
            )

            with patch.dict(os.environ, {"HOME": str(home)}):
                merged = load_config(user_config_path)

            self.assertEqual(merged["directories"]["repositories"], "/USER/Repos")
            self.assertEqual(merged["directories"]["binaries"], "/USER/bin")

    def test_load_config_falls_back_to_package_when_user_dir_has_no_defaults(self):
        with tempfile.TemporaryDirectory() as td:
            home = Path(td) / "home"
            user_cfg_dir = home / ".config" / "pkgmgr"
            user_cfg_dir.mkdir(parents=True)
            user_config_path = str(user_cfg_dir / "config.yaml")

            # Only user config exists, no other yaml defaults
            (user_cfg_dir / "config.yaml").write_text(
                yaml.safe_dump({"directories": {"x": 1}}), encoding="utf-8"
            )

            # Provide package defaults via fake pkgmgr + pkg_root/config
            root = Path(td) / "site-packages"
            pkg_root = root / "pkgmgr"
            cfg_dir = (
                root / "config"
            )  # NOTE: load.py checks multiple roots, including pkg_root.parent (=site-packages)
            pkg_root.mkdir(parents=True)
            cfg_dir.mkdir(parents=True)

            (cfg_dir / "defaults.yaml").write_text(
                yaml.safe_dump(
                    {"directories": {"repositories": "/PKG/Repos"}, "repositories": []}
                ),
                encoding="utf-8",
            )

            fake_pkgmgr = types.SimpleNamespace(__file__=str(pkg_root / "__init__.py"))
            with patch.dict(sys.modules, {"pkgmgr": fake_pkgmgr}):
                with patch.dict(os.environ, {"HOME": str(home)}):
                    merged = load_config(user_config_path)

            # directories are merged: defaults then user
            self.assertEqual(merged["directories"]["repositories"], "/PKG/Repos")
            self.assertEqual(merged["directories"]["x"], 1)
            self.assertIn("repositories", merged)
            self.assertIsInstance(merged["repositories"], list)


if __name__ == "__main__":
    unittest.main()
