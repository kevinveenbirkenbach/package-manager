from __future__ import annotations

import os
from typing import Dict, Any

from .model import RepoParts


class CreateRepoPlanner:
    def __init__(self, parts: RepoParts, repositories_base_dir: str):
        self.parts = parts
        self.repositories_base_dir = os.path.expanduser(repositories_base_dir)

    @property
    def repo_dir(self) -> str:
        return os.path.join(
            self.repositories_base_dir,
            self.parts.host,
            self.parts.owner,
            self.parts.name,
        )

    @property
    def homepage(self) -> str:
        return f"https://{self.parts.host}/{self.parts.owner}/{self.parts.name}"

    @property
    def primary_remote(self) -> str:
        if self.parts.port:
            return (
                f"ssh://git@{self.parts.host}:{self.parts.port}/"
                f"{self.parts.owner}/{self.parts.name}.git"
            )
        return f"git@{self.parts.host}:{self.parts.owner}/{self.parts.name}.git"

    def template_context(
        self,
        *,
        author_name: str,
        author_email: str,
    ) -> Dict[str, Any]:
        return {
            "provider": self.parts.host,
            "port": self.parts.port,
            "account": self.parts.owner,
            "repository": self.parts.name,
            "homepage": self.homepage,
            "author_name": author_name,
            "author_email": author_email,
            "license_text": f"All rights reserved by {author_name}",
            "primary_remote": self.primary_remote,
        }
