from __future__ import annotations

import os
from typing import Dict, Any, Set

import yaml

from pkgmgr.core.command.alias import generate_alias
from pkgmgr.core.config.save import save_user_config

Repository = Dict[str, Any]


class ConfigRepoWriter:
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

    def ensure_repo_entry(
        self,
        *,
        host: str,
        port: str | None,
        owner: str,
        name: str,
        homepage: str,
        preview: bool,
    ) -> Repository:
        repositories = self.config_merged.setdefault("repositories", [])

        for repo in repositories:
            if (
                repo.get("provider") == host
                and repo.get("account") == owner
                and repo.get("repository") == name
            ):
                return repo

        existing_aliases: Set[str] = {
            str(r.get("alias")) for r in repositories if r.get("alias")
        }

        repo: Repository = {
            "provider": host,
            "port": port,
            "account": owner,
            "repository": name,
            "homepage": homepage,
            "alias": generate_alias(
                {
                    "repository": name,
                    "provider": host,
                    "account": owner,
                },
                self.bin_dir,
                existing_aliases=existing_aliases,
            ),
            "verified": {},
        }

        if preview:
            print(f"[Preview] Would add repository to config: {repo}")
            return repo

        if os.path.exists(self.user_config_path):
            with open(self.user_config_path, "r", encoding="utf-8") as f:
                user_cfg = yaml.safe_load(f) or {}
        else:
            user_cfg = {}

        user_cfg.setdefault("repositories", []).append(repo)
        save_user_config(user_cfg, self.user_config_path)

        repositories.append(repo)
        print(f"[INFO] Added repository to configuration: {host}/{owner}/{name}")

        return repo
