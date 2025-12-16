from __future__ import annotations

import os
from typing import Dict, Any

from pkgmgr.core.git.queries import get_config_value

from .parser import parse_identifier
from .planner import CreateRepoPlanner
from .config_writer import ConfigRepoWriter
from .templates import TemplateRenderer
from .git_bootstrap import GitBootstrapper
from .mirrors import MirrorBootstrapper


class CreateRepoService:
    def __init__(
        self,
        *,
        config_merged: Dict[str, Any],
        user_config_path: str,
        bin_dir: str,
    ):
        self.config_merged = config_merged
        self.user_config_path = user_config_path
        self.bin_dir = bin_dir

        self.templates = TemplateRenderer()
        self.git = GitBootstrapper()
        self.mirrors = MirrorBootstrapper()

    def run(
        self,
        *,
        identifier: str,
        preview: bool,
        remote: bool,
    ) -> None:
        parts = parse_identifier(identifier)

        base_dir = self.config_merged.get("directories", {}).get(
            "repositories", "~/Repositories"
        )

        planner = CreateRepoPlanner(parts, base_dir)

        writer = ConfigRepoWriter(
            config_merged=self.config_merged,
            user_config_path=self.user_config_path,
            bin_dir=self.bin_dir,
        )

        repo = writer.ensure_repo_entry(
            host=parts.host,
            port=parts.port,
            owner=parts.owner,
            name=parts.name,
            homepage=planner.homepage,
            preview=preview,
        )

        if preview:
            print(f"[Preview] Would ensure directory exists: {planner.repo_dir}")
        else:
            os.makedirs(planner.repo_dir, exist_ok=True)

        author_name = get_config_value("user.name") or "Unknown Author"
        author_email = get_config_value("user.email") or "unknown@example.invalid"

        self.templates.render(
            repo_dir=planner.repo_dir,
            context=planner.template_context(
                author_name=author_name,
                author_email=author_email,
            ),
            preview=preview,
        )

        self.git.init_repo(planner.repo_dir, preview=preview)

        self.mirrors.write_defaults(
            repo_dir=planner.repo_dir,
            primary=planner.primary_remote,
            name=parts.name,
            preview=preview,
        )

        self.mirrors.setup(
            repo=repo,
            repositories_base_dir=os.path.expanduser(base_dir),
            all_repos=self.config_merged.get("repositories", []),
            preview=preview,
            remote=remote,
        )

        if remote:
            self.git.push_default_branch(planner.repo_dir, preview=preview)
