from __future__ import annotations

import os
from typing import Dict, List, Tuple, Optional

import yaml

from pkgmgr.core.config.save import save_user_config

from .context import build_context
from .io import write_mirrors_file
from .types import MirrorMap, Repository


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _repo_key(repo: Repository) -> Tuple[str, str, str]:
    """
    Normalised key for identifying a repository in config files.
    """
    return (
        str(repo.get("provider", "")),
        str(repo.get("account", "")),
        str(repo.get("repository", "")),
    )


def _load_user_config(path: str) -> Dict[str, object]:
    """
    Load a user config YAML file as dict.
    Non-dicts yield {}.
    """
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


# -----------------------------------------------------------------------------
# Main merge command
# -----------------------------------------------------------------------------


def merge_mirrors(
    selected_repos: List[Repository],
    repositories_base_dir: str,
    all_repos: List[Repository],
    source: str,
    target: str,
    preview: bool = False,
    user_config_path: Optional[str] = None,
) -> None:
    """
    Merge mirrors between config and MIRRORS file.

    Rules:
      - source, target ∈ {"config", "file"}.
      - merged = (target_mirrors overridden by source_mirrors)
      - If target == "file" → write MIRRORS file.
      - If target == "config":
            * update the user config YAML directly
            * write it using save_user_config()

    The merge strategy is:
        dst + src  (src wins on same name)
    """

    # Load user config once if we intend to write to it.
    user_cfg: Optional[Dict[str, object]] = None
    user_cfg_path_expanded: Optional[str] = None

    if target == "config" and user_config_path and not preview:
        user_cfg_path_expanded = os.path.expanduser(user_config_path)
        user_cfg = _load_user_config(user_cfg_path_expanded)
        if not isinstance(user_cfg.get("repositories"), list):
            user_cfg["repositories"] = []

    for repo in selected_repos:
        ctx = build_context(repo, repositories_base_dir, all_repos)

        print("============================================================")
        print(f"[MIRROR MERGE] Repository: {ctx.identifier}")
        print(f"[MIRROR MERGE] Directory:  {ctx.repo_dir}")
        print(f"[MIRROR MERGE] {source} → {target}")
        print("============================================================")

        # Pick the correct source/target maps
        if source == "config":
            src = ctx.config_mirrors
            dst = ctx.file_mirrors
        else:  # source == "file"
            src = ctx.file_mirrors
            dst = ctx.config_mirrors

        # Merge (src overrides dst)
        merged: MirrorMap = dict(dst)
        merged.update(src)

        # ---------------------------------------------------------
        # WRITE TO FILE
        # ---------------------------------------------------------
        if target == "file":
            write_mirrors_file(ctx.repo_dir, merged, preview=preview)
            print()
            continue

        # ---------------------------------------------------------
        # WRITE TO CONFIG
        # ---------------------------------------------------------
        if target == "config":
            # If preview or no config path → show intended output
            if preview or not user_cfg:
                print("[INFO] The following mirrors would be written to config:")
                if not merged:
                    print("       (no mirrors)")
                else:
                    for name, url in sorted(merged.items()):
                        print(f"       - {name}: {url}")
                print("       (Config not modified due to preview or missing path.)")
                print()
                continue

            repos = user_cfg.get("repositories")
            target_key = _repo_key(repo)
            existing_repo: Optional[Repository] = None

            # Find existing repo entry
            for entry in repos:
                if isinstance(entry, dict) and _repo_key(entry) == target_key:
                    existing_repo = entry
                    break

            # Create entry if missing
            if existing_repo is None:
                existing_repo = {
                    "provider": repo.get("provider"),
                    "account": repo.get("account"),
                    "repository": repo.get("repository"),
                }
                repos.append(existing_repo)

            # Write or delete mirrors
            if merged:
                existing_repo["mirrors"] = dict(merged)
            else:
                existing_repo.pop("mirrors", None)

            print("       [OK] Updated repo['mirrors'] in user config.")
            print()

    # -------------------------------------------------------------
    # SAVE CONFIG (once at the end)
    # -------------------------------------------------------------
    if user_cfg is not None and user_cfg_path_expanded is not None and not preview:
        save_user_config(user_cfg, user_cfg_path_expanded)
        print(f"[OK] Saved updated config: {user_cfg_path_expanded}")
