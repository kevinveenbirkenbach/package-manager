from __future__ import annotations

import os
import unittest
from pathlib import Path

from pkgmgr.core.repository.paths import resolve_repo_paths


def _find_repo_root() -> Path:
    """
    Locate the pkgmgr repository root from the test location.

    Assumes:
      repo_root/
        src/pkgmgr/...
        tests/integration/...
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "src" / "pkgmgr").is_dir():
            return parent
    raise RuntimeError("Could not determine repository root for pkgmgr integration test")


class TestRepositoryPathsExist(unittest.TestCase):
    """
    Integration test: pkgmgr is the TEMPLATE repository.
    All canonical paths resolved for pkgmgr must exist.
    """

    def test_pkgmgr_repository_paths_exist(self) -> None:
        repo_root = _find_repo_root()
        paths = resolve_repo_paths(str(repo_root))

        missing: list[str] = []

        def require(path: str | None, description: str) -> None:
            if not path:
                missing.append(f"{description}: <not resolved>")
                return
            if not os.path.isfile(path):
                missing.append(f"{description}: {path} (missing)")

        # Core metadata
        require(paths.pyproject_toml, "pyproject.toml")
        require(paths.flake_nix, "flake.nix")

        # Human changelog
        require(paths.changelog_md, "CHANGELOG.md")

        # Packaging files (pkgmgr defines the template)
        require(paths.arch_pkgbuild, "Arch PKGBUILD")
        require(paths.debian_changelog, "Debian changelog")
        require(paths.rpm_spec, "RPM spec file")

        if missing:
            self.fail(
                "pkgmgr repository does not satisfy the canonical repository layout:\n"
                + "\n".join(f"  - {item}" for item in missing)
            )


if __name__ == "__main__":
    unittest.main()
