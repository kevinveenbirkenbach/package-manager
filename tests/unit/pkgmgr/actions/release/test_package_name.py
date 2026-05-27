"""Unit tests for `pkgmgr.actions.release.package_name.resolve_package_name`.

The resolver must prefer the explicit name from existing packaging files
over the repository folder name so that renaming the folder does not
silently rename the distro package.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from typing import Optional

from pkgmgr.actions.release.package_name import resolve_package_name
from pkgmgr.core.repository.paths import RepoPaths


def _paths(
    repo_dir: str,
    *,
    debian_control: Optional[str] = None,
    arch_pkgbuild: Optional[str] = None,
    rpm_spec: Optional[str] = None,
) -> RepoPaths:
    return RepoPaths(
        repo_dir=repo_dir,
        pyproject_toml=os.path.join(repo_dir, "pyproject.toml"),
        flake_nix=os.path.join(repo_dir, "flake.nix"),
        changelog_md=None,
        arch_pkgbuild=arch_pkgbuild,
        debian_changelog=None,
        debian_control=debian_control,
        rpm_spec=rpm_spec,
    )


class TestResolvePackageName(unittest.TestCase):
    def test_debian_control_wins_over_folder(self) -> None:
        with tempfile.TemporaryDirectory(prefix="infinito-nexus-core_") as repo:
            control = Path(repo) / "control"
            control.write_text(
                "Source: infinito-nexus\nPackage: infinito-nexus\n",
                encoding="utf-8",
            )
            self.assertEqual(
                resolve_package_name(_paths(repo, debian_control=str(control))),
                "infinito-nexus",
            )

    def test_pkgbuild_used_when_no_control(self) -> None:
        with tempfile.TemporaryDirectory(prefix="infinito-nexus-core_") as repo:
            pkgbuild = Path(repo) / "PKGBUILD"
            pkgbuild.write_text(
                "pkgname=infinito-nexus\npkgver=1.0\n", encoding="utf-8"
            )
            self.assertEqual(
                resolve_package_name(_paths(repo, arch_pkgbuild=str(pkgbuild))),
                "infinito-nexus",
            )

    def test_rpm_spec_used_when_no_control_no_pkgbuild(self) -> None:
        with tempfile.TemporaryDirectory(prefix="infinito-nexus-core_") as repo:
            spec = Path(repo) / "pkg.spec"
            spec.write_text("Name:           infinito-nexus\n", encoding="utf-8")
            self.assertEqual(
                resolve_package_name(_paths(repo, rpm_spec=str(spec))),
                "infinito-nexus",
            )

    def test_folder_fallback_when_no_packaging_metadata(self) -> None:
        with tempfile.TemporaryDirectory(prefix="solo-tool_") as repo:
            self.assertEqual(
                resolve_package_name(_paths(repo)),
                os.path.basename(repo),
            )

    def test_priority_debian_over_pkgbuild_over_spec(self) -> None:
        with tempfile.TemporaryDirectory() as repo:
            control = Path(repo) / "control"
            control.write_text("Package: deb-name\n", encoding="utf-8")
            pkgbuild = Path(repo) / "PKGBUILD"
            pkgbuild.write_text("pkgname=arch-name\n", encoding="utf-8")
            spec = Path(repo) / "x.spec"
            spec.write_text("Name: rpm-name\n", encoding="utf-8")
            self.assertEqual(
                resolve_package_name(
                    _paths(
                        repo,
                        debian_control=str(control),
                        arch_pkgbuild=str(pkgbuild),
                        rpm_spec=str(spec),
                    )
                ),
                "deb-name",
            )

    def test_strips_quotes_in_pkgbuild(self) -> None:
        with tempfile.TemporaryDirectory() as repo:
            pkgbuild = Path(repo) / "PKGBUILD"
            pkgbuild.write_text("pkgname='quoted-name'\n", encoding="utf-8")
            self.assertEqual(
                resolve_package_name(_paths(repo, arch_pkgbuild=str(pkgbuild))),
                "quoted-name",
            )


if __name__ == "__main__":
    unittest.main()
