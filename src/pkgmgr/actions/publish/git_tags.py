from __future__ import annotations

from pkgmgr.core.git.queries import get_tags_at_ref
from pkgmgr.core.version.semver import SemVer, is_semver_tag


def head_semver_tags(cwd: str = ".") -> list[str]:
    tags = get_tags_at_ref("HEAD", cwd=cwd)
    tags = [t for t in tags if is_semver_tag(t) and t.startswith("v")]
    return sorted(tags, key=SemVer.parse)
