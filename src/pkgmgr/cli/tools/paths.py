from __future__ import annotations

from typing import Any, Dict

from pkgmgr.cli.context import CLIContext
from pkgmgr.core.repository.dir import get_repo_dir

Repository = Dict[str, Any]


def resolve_repository_path(repository: Repository, ctx: CLIContext) -> str:
    """
    Resolve the filesystem path for a repository.

    Priority:
      1. Use explicit keys if present (directory / path / workspace / workspace_dir).
      2. Fallback to get_repo_dir(...) using the repositories base directory
         from the CLI context.
    """
    for key in ("directory", "path", "workspace", "workspace_dir"):
        value = repository.get(key)
        if value:
            return value

    base_dir = getattr(ctx, "repositories_base_dir", None) or getattr(
        ctx, "repositories_dir", None
    )
    if not base_dir:
        raise RuntimeError(
            "Cannot resolve repositories base directory from context; "
            "expected ctx.repositories_base_dir or ctx.repositories_dir."
        )

    return get_repo_dir(base_dir, repository)
