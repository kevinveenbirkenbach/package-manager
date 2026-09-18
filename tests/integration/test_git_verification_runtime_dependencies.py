from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()
