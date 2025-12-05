#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer for Ansible dependencies defined in requirements.yml.

This installer installs collections and roles via ansible-galaxy when found.
"""

import os
import tempfile
from typing import Any, Dict, List

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

    def _validate_requirements(self, requirements: Dict[str, Any], identifier: str) -> None:
        """
        Validate the requirements.yml structure.
        Raises SystemExit on any validation error.
        """

        errors: List[str] = []

        if not isinstance(requirements, dict):
            errors.append("Top-level structure must be a mapping.")

        else:
            allowed_keys = {"collections", "roles"}
            unknown_keys = set(requirements.keys()) - allowed_keys
            if unknown_keys:
                print(
                    f"Warning: requirements.yml in {identifier} contains unknown keys: "
                    f"{', '.join(sorted(unknown_keys))}"
                )

            for section in ("collections", "roles"):
                if section not in requirements:
                    continue

                value = requirements[section]
                if not isinstance(value, list):
                    errors.append(f"'{section}' must be a list.")
                    continue

                for idx, entry in enumerate(value):
                    if isinstance(entry, str):
                        # short form "community.docker" etc.
                        continue

                    if isinstance(entry, dict):
                        # Collections: brauchen zwingend 'name'
                        if section == "collections":
                            if not entry.get("name"):
                                errors.append(
                                    f"Entry #{idx} in '{section}' is a mapping "
                                    f"but has no 'name' key."
                                )
                        else:
                            # Roles: 'name' ODER 'src' sind ok (beides gängig)
                            if not (entry.get("name") or entry.get("src")):
                                errors.append(
                                    f"Entry #{idx} in '{section}' is a mapping but "
                                    f"has neither 'name' nor 'src' key."
                                )
                        continue

                    errors.append(
                        f"Entry #{idx} in '{section}' has invalid type "
                        f"{type(entry).__name__}; expected string or mapping."
                    )

        if errors:
            print(f"Invalid requirements.yml in {identifier}:")
            for err in errors:
                print(f"  - {err}")
            raise SystemExit(
                f"requirements.yml validation failed for {identifier}."
            )

    def run(self, ctx: RepoContext) -> None:
        req_file = os.path.join(ctx.repo_dir, self.REQUIREMENTS_FILE)
        requirements = self._load_requirements(req_file, ctx.identifier)
        if not requirements:
            return

        # Validate structure before doing anything dangerous
        self._validate_requirements(requirements, ctx.identifier)

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
