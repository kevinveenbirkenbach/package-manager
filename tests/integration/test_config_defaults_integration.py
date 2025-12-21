# tests/integration/test_config_defaults_integration.py
from __future__ import annotations

import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from pkgmgr.core.config.load import load_config
from pkgmgr.cli.commands import config as config_cmd


class ConfigDefaultsIntegrationTest(unittest.TestCase):
    def test_defaults_yaml_is_loaded_and_can_be_copied_to_user_config_dir(self):
        """
        Integration test:
        - Create a temp "site-packages/pkgmgr" fake install root
        - Put defaults under "<pkg_root>/config/defaults.yaml"
        - Verify:
            A) load_config() picks up defaults from that config folder when user dir has no defaults
            B) _update_default_configs() copies defaults.yaml into ~/.config/pkgmgr/
        """
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            # Fake HOME for user config
            home = root / "home"
            user_cfg_dir = home / ".config" / "pkgmgr"
            user_cfg_dir.mkdir(parents=True)
            user_config_path = str(user_cfg_dir / "config.yaml")

            # Create a user config file that should NOT be overwritten by update
            (user_cfg_dir / "config.yaml").write_text(
                yaml.safe_dump({"directories": {"user_only": "/home/user"}}),
                encoding="utf-8",
            )

            # Fake pkg install layout:
            # pkg_root = <root>/site-packages/pkgmgr
            site_packages = root / "site-packages"
            pkg_root = site_packages / "pkgmgr"
            pkg_root.mkdir(parents=True)

            # defaults live inside the package now: <pkg_root>/config/defaults.yaml
            config_dir = pkg_root / "config"
            config_dir.mkdir(parents=True)

            defaults_payload = {
                "directories": {
                    "repositories": "/opt/Repositories",
                    "binaries": "/usr/local/bin",
                },
                "repositories": [
                    {"provider": "github", "account": "acme", "repository": "demo"}
                ],
            }
            (config_dir / "defaults.yaml").write_text(
                yaml.safe_dump(defaults_payload),
                encoding="utf-8",
            )

            # Provide fake pkgmgr module so your functions resolve pkg_root correctly
            fake_pkgmgr = types.SimpleNamespace(__file__=str(pkg_root / "__init__.py"))

            with patch.dict(sys.modules, {"pkgmgr": fake_pkgmgr}):
                with patch.dict(os.environ, {"HOME": str(home)}):
                    # A) load_config should fall back to <pkg_root>/config/defaults.yaml
                    merged = load_config(user_config_path)

                    self.assertEqual(
                        merged["directories"]["repositories"], "/opt/Repositories"
                    )
                    self.assertEqual(
                        merged["directories"]["binaries"], "/usr/local/bin"
                    )

                    # user-only key must still exist (user config merges over defaults)
                    self.assertEqual(merged["directories"]["user_only"], "/home/user")

                    self.assertIn("repositories", merged)
                    self.assertTrue(
                        any(
                            r.get("provider") == "github"
                            and r.get("account") == "acme"
                            and r.get("repository") == "demo"
                            for r in merged["repositories"]
                        )
                    )

                    # B) update_default_configs should copy defaults.yaml to ~/.config/pkgmgr/
                    before_config_yaml = (user_cfg_dir / "config.yaml").read_text(
                        encoding="utf-8"
                    )

                    config_cmd._update_default_configs(user_config_path)

                    self.assertTrue((user_cfg_dir / "defaults.yaml").is_file())
                    copied_defaults = yaml.safe_load(
                        (user_cfg_dir / "defaults.yaml").read_text(encoding="utf-8")
                    )
                    self.assertEqual(
                        copied_defaults["directories"]["repositories"],
                        "/opt/Repositories",
                    )

                    after_config_yaml = (user_cfg_dir / "config.yaml").read_text(
                        encoding="utf-8"
                    )
                    self.assertEqual(after_config_yaml, before_config_yaml)


if __name__ == "__main__":
    unittest.main()
