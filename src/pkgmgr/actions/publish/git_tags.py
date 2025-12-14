from __future__ import annotations

from pkgmgr.core.git import run_git
from pkgmgr.core.version.semver import SemVer, is_semver_tag


def head_semver_tags(cwd: str = ".") -> list[str]:
    out = run_git(["tag", "--points-at", "HEAD"], cwd=cwd)
    if not out:
        return []

    tags = [t.strip() for t in out.splitlines() if t.strip()]
    tags = [t for t in tags if is_semver_tag(t) and t.startswith("v")]
    if not tags:
        return []

    return sorted(tags, key=SemVer.parse)
