from __future__ import annotations

from typing import List

from pkgmgr.core.repository.dir import get_repo_dir
from pkgmgr.core.repository.identifier import get_repo_identifier

from .io import load_config_mirrors, read_mirrors_file
from .types import MirrorMap, RepoMirrorContext, Repository


def build_context(
    repo: Repository,
    repositories_base_dir: str,
    all_repos: List[Repository],
) -> RepoMirrorContext:
    """
    Build a RepoMirrorContext for a single repository.
    """
    identifier = get_repo_identifier(repo, all_repos)
    repo_dir = get_repo_dir(repositories_base_dir, repo)

    config_mirrors: MirrorMap = load_config_mirrors(repo)
    file_mirrors: MirrorMap = read_mirrors_file(repo_dir)

    return RepoMirrorContext(
        identifier=identifier,
        repo_dir=repo_dir,
        config_mirrors=config_mirrors,
        file_mirrors=file_mirrors,
    )
