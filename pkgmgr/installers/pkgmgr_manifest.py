#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Installer for pkgmgr.yml manifest dependencies.

This installer reads pkgmgr.yml (if present) and installs referenced pkgmgr
repository dependencies via pkgmgr itself.
"""

import os
from typing import Any, Dict, List

import yaml

from pkgmgr.context import RepoContext
from pkgmgr.installers.base import BaseInstaller
from pkgmgr.run_command import run_command


class PkgmgrManifestInstaller(BaseInstaller):
    """Install pkgmgr-defined repository dependencies from pkgmgr.yml."""

    MANIFEST_NAME = "pkgmgr.yml"

    def supports(self, ctx: RepoContext) -> bool:
        manifest_path = os.path.join(ctx.repo_dir, self.MANIFEST_NAME)
        return os.path.exists(manifest_path)

    def _load_manifest(self, manifest_path: str) -> Dict[str, Any]:
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as exc:
            print(f"Error loading {self.MANIFEST_NAME} in '{manifest_path}': {exc}")
            return {}

    def _collect_dependency_ids(self, dependencies: List[Dict[str, Any]]) -> List[str]:
        ids: List[str] = []
        for dep in dependencies:
            if not isinstance(dep, dict):
                continue
            repo_id = dep.get("repository")
            if repo_id:
                ids.append(str(repo_id))
        return ids

    def run(self, ctx: RepoContext) -> None:
        manifest_path = os.path.join(ctx.repo_dir, self.MANIFEST_NAME)
        manifest = self._load_manifest(manifest_path)
        if not manifest:
            return

        dependencies = manifest.get("dependencies", []) or []
        if not isinstance(dependencies, list) or not dependencies:
            return

        author = manifest.get("author")
        url = manifest.get("url")
        description = manifest.get("description")

        if not ctx.preview:
            print("pkgmgr manifest detected:")
            if author:
                print(f"  author: {author}")
            if url:
                print(f"  url: {url}")
            if description:
                print(f"  description: {description}")

        dep_repo_ids = self._collect_dependency_ids(dependencies)

        if ctx.update_dependencies and dep_repo_ids:
            cmd_pull = "pkgmgr pull " + " ".join(dep_repo_ids)
            try:
                run_command(cmd_pull, preview=ctx.preview)
            except SystemExit as exc:
                print(f"Warning: 'pkgmgr pull' for dependencies failed (exit code {exc}).")

        # Install dependencies one by one
        for dep in dependencies:
            if not isinstance(dep, dict):
                continue

            repo_id = dep.get("repository")
            if not repo_id:
                continue

            version = dep.get("version")
            reason = dep.get("reason")

            if reason and not ctx.preview:
                print(f"Installing dependency {repo_id}: {reason}")
            else:
                print(f"Installing dependency {repo_id}...")

            cmd = f"pkgmgr install {repo_id}"

            if version:
                cmd += f" --version {version}"

            if ctx.no_verification:
                cmd += " --no-verification"

            if ctx.update_dependencies:
                cmd += " --dependencies"

            if ctx.clone_mode:
                cmd += f" --clone-mode {ctx.clone_mode}"

            try:
                run_command(cmd, preview=ctx.preview)
            except SystemExit as exc:
                print(f"[Warning] Failed to install dependency '{repo_id}': {exc}")
