from __future__ import annotations

from typing import Any, Dict

from .service import CreateRepoService

RepositoryConfig = Dict[str, Any]

__all__ = [
    "CreateRepoService",
    "create_repo",
]


def create_repo(
    identifier: str,
    config_merged: RepositoryConfig,
    user_config_path: str,
    bin_dir: str,
    *,
    remote: bool = False,
    preview: bool = False,
) -> None:
    CreateRepoService(
        config_merged=config_merged,
        user_config_path=user_config_path,
        bin_dir=bin_dir,
    ).run(identifier=identifier, preview=preview, remote=remote)
