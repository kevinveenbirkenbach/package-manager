# tests/integration/test_repository_paths_exist.py
from __future__ import annotations

import os
from pathlib import Path

import pytest

from pkgmgr.core.repository.paths import resolve_repo_paths


def _find_repo_root() -> Path:
    """
    Locate the pkgmgr repository root from the test location.

    This assumes the standard layout:
      repo_root/
        src/pkgmgr/...
        tests/integration/...
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").is_file() and (parent / "src" / "pkgmgr").is_dir():
            return parent
    raise RuntimeError("Could not determine repository root for pkgmgr integration test")


def test_pkgmgr_repository_paths_exist() -> None:
    """
    Integration test: verify that the pkgmgr repository provides all
    canonical files defined by RepoPaths.

    pkgmgr acts as the TEMPLATE repository for all other packages.
    Therefore, every path resolved here is expected to exist.
    """
    repo_root = _find_repo_root()
    paths = resolve_repo_paths(str(repo_root))

    missing: list[str] = []

    def _require(path: str | None, description: str) -> None:
        if not path:
            missing.append(f"{description}: <not resolved>")
            return
        if not os.path.isfile(path):
            missing.append(f"{description}: {path} (missing)")

    # Core metadata (must always exist)
    _require(paths.pyproject_toml, "pyproject.toml")
    _require(paths.flake_nix, "flake.nix")

    # Human-facing changelog (pkgmgr must provide one)
    _require(paths.changelog_md, "CHANGELOG.md")

    # Packaging files (pkgmgr is the reference implementation)
    _require(paths.arch_pkgbuild, "Arch PKGBUILD")
    _require(paths.debian_changelog, "Debian changelog")
    _require(paths.rpm_spec, "RPM spec file")

    if missing:
        pytest.fail(
            "pkgmgr repository does not satisfy the canonical repository layout:\n"
            + "\n".join(f"  - {item}" for item in missing)
        )
