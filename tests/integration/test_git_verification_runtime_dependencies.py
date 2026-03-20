from __future__ import annotations

import re
import unittest
from pathlib import Path


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file() and (
            parent / "src" / "pkgmgr"
        ).is_dir():
            return parent
    raise RuntimeError(
        "Could not determine repository root for pkgmgr integration test"
    )


class TestGitVerificationRuntimeDependencies(unittest.TestCase):
    def test_flake_app_includes_git_and_gpg_runtime_tools(self) -> None:
        repo_root = _find_repo_root()
        flake_text = (repo_root / "flake.nix").read_text(encoding="utf-8")

        self.assertIn("pkgs.git", flake_text)
        self.assertIn("pkgs.gnupg", flake_text)

    def test_distro_dependency_scripts_install_gpg_tools(self) -> None:
        repo_root = _find_repo_root()
        expected_packages = {
            "arch": "gnupg",
            "debian": "gnupg",
            "ubuntu": "gnupg",
            "fedora": "gnupg2",
            "centos": "gnupg2",
        }

        missing: list[str] = []
        for distro, package_name in expected_packages.items():
            script_path = (
                repo_root / "scripts" / "installation" / distro / "dependencies.sh"
            )
            content = script_path.read_text(encoding="utf-8")
            if not re.search(rf"\b{re.escape(package_name)}\b", content):
                missing.append(
                    f"{distro}: expected package {package_name} in {script_path}"
                )

        if missing:
            self.fail(
                "Git signature verification runtime dependencies are incomplete:\n"
                + "\n".join(f"  - {item}" for item in missing)
            )


if __name__ == "__main__":
    unittest.main()
