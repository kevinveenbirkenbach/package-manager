#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer for Ansible dependencies defined in requirements.yml.

This installer installs collections and roles via ansible-galaxy when found.
"""

import os
import tempfile
from typing import Any, Dict

import yaml

from pkgmgr.context import RepoContext
from pkgmgr.installers.base import BaseInstaller
from pkgmgr.run_command import run_command


class AnsibleRequirementsInstaller(BaseInstaller):
    """Install Ansible collections and roles from requirements.yml."""

    REQUIREMENTS_FILE = "requirements.yml"

    def supports(self, ctx: RepoContext) -> bool:
        req_file = os.path.join(ctx.repo_dir, self.REQUIREMENTS_FILE)
        return os.path.exists(req_file)

    def _load_requirements(self, req_path: str, identifier: str) -> Dict[str, Any]:
        try:
            with open(req_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as exc:
            print(f"Error loading {self.REQUIREMENTS_FILE} in {identifier}: {exc}")
            return {}

    def run(self, ctx: RepoContext) -> None:
        req_file = os.path.join(ctx.repo_dir, self.REQUIREMENTS_FILE)
        requirements = self._load_requirements(req_file, ctx.identifier)
        if not requirements or not isinstance(requirements, dict):
            return

        if "collections" not in requirements and "roles" not in requirements:
            return

        print(f"Ansible dependencies found in {ctx.identifier}, installing...")

        ansible_requirements: Dict[str, Any] = {}
        if "collections" in requirements:
            ansible_requirements["collections"] = requirements["collections"]
        if "roles" in requirements:
            ansible_requirements["roles"] = requirements["roles"]

        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".yml",
            delete=False,
        ) as tmp:
            yaml.dump(ansible_requirements, tmp, default_flow_style=False)
            tmp_filename = tmp.name

        if "collections" in ansible_requirements:
            print(f"Ansible collections found in {ctx.identifier}, installing...")
            cmd = f"ansible-galaxy collection install -r {tmp_filename}"
            run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)

        if "roles" in ansible_requirements:
            print(f"Ansible roles found in {ctx.identifier}, installing...")
            cmd = f"ansible-galaxy role install -r {tmp_filename}"
            run_command(cmd, cwd=ctx.repo_dir, preview=ctx.preview)
