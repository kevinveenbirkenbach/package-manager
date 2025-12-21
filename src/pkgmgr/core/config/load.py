# src/pkgmgr/core/config/load.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Load and merge pkgmgr configuration.

Layering rules:

1. Defaults / category files:
   - First load all *.yml/*.yaml (except config.yaml) from the user directory:
         ~/.config/pkgmgr/

   - If no matching files exist there, fall back to defaults shipped with pkgmgr:

         <pkg_root>/config

     During development (src-layout), we optionally also check:
         <repo_root>/config

     All *.yml/*.yaml files are loaded as layers.

   - The filename stem is used as category name and stored in repo["category_files"].

2. User config:
   - ~/.config/pkgmgr/config.yaml (or the provided path)
     is loaded and merged over defaults:
       - directories: dict deep-merge
       - repositories: per _merge_repo_lists (no deletions!)

3. Result:
   - A dict with at least:
       config["directories"]  (dict)
       config["repositories"] (list[dict])
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

Repo = Dict[str, Any]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge two dictionaries.

    Values from `override` win over values in `base`.
    """
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


def _repo_key(repo: Repo) -> Tuple[str, str, str]:
    """
    Normalised key for identifying a repository across config files.
    """
    return (
        str(repo.get("provider", "")),
        str(repo.get("account", "")),
        str(repo.get("repository", "")),
    )


def _merge_repo_lists(
    base_list: List[Repo],
    new_list: List[Repo],
    category_name: Optional[str] = None,
) -> List[Repo]:
    """
    Merge two repository lists, matching by (provider, account, repository).

    - If a repo from new_list does not exist, it is added.
    - If it exists, its fields are deep-merged (override wins).
    - If category_name is set, it is appended to repo["category_files"].
    """
    index: Dict[Tuple[str, str, str], Repo] = {_repo_key(r): r for r in base_list}

    for src in new_list:
        key = _repo_key(src)
        if key == ("", "", ""):
            # Incomplete key -> append as-is
            dst = dict(src)
            if category_name:
                dst.setdefault("category_files", [])
                if category_name not in dst["category_files"]:
                    dst["category_files"].append(category_name)
            base_list.append(dst)
            continue

        existing = index.get(key)
        if existing is None:
            dst = dict(src)
            if category_name:
                dst.setdefault("category_files", [])
                if category_name not in dst["category_files"]:
                    dst["category_files"].append(category_name)
            base_list.append(dst)
            index[key] = dst
        else:
            _deep_merge(existing, src)
            if category_name:
                existing.setdefault("category_files", [])
                if category_name not in existing["category_files"]:
                    existing["category_files"].append(category_name)

    return base_list


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    """
    Load a single YAML file as dict. Non-dicts yield {}.
    """
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return {}
    return data


def _load_layer_dir(
    config_dir: Path,
    skip_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Load all *.yml/*.yaml from a directory as layered defaults.

    - skip_filename: filename (e.g. "config.yaml") to ignore.

    Returns:
      {
        "directories": {...},
        "repositories": [...],
      }
    """
    defaults: Dict[str, Any] = {"directories": {}, "repositories": []}

    if not config_dir.is_dir():
        return defaults

    yaml_files = [
        p
        for p in config_dir.iterdir()
        if p.is_file()
        and p.suffix.lower() in (".yml", ".yaml")
        and (skip_filename is None or p.name != skip_filename)
    ]
    if not yaml_files:
        return defaults

    yaml_files.sort(key=lambda p: p.name)

    for path in yaml_files:
        data = _load_yaml_file(path)
        category_name = path.stem

        dirs = data.get("directories")
        if isinstance(dirs, dict):
            defaults.setdefault("directories", {})
            _deep_merge(defaults["directories"], dirs)

        repos = data.get("repositories")
        if isinstance(repos, list):
            defaults.setdefault("repositories", [])
            _merge_repo_lists(
                defaults["repositories"],
                repos,
                category_name=category_name,
            )

    return defaults


def _load_defaults_from_package_or_project() -> Dict[str, Any]:
    """
    Fallback: load default configs from possible install or dev layouts.

    Supported locations:
      - <pkg_root>/config                (installed wheel / editable)
      - <repo_root>/config               (optional dev fallback when pkg_root is src/pkgmgr)
    """
    try:
        import pkgmgr  # type: ignore
    except Exception:
        return {"directories": {}, "repositories": []}

    pkg_root = Path(pkgmgr.__file__).resolve().parent
    candidates: List[Path] = []

    # Always prefer package-internal config dir
    candidates.append(pkg_root / "config")

    # Dev fallback: repo_root/src/pkgmgr -> repo_root/config
    parent = pkg_root.parent
    if parent.name == "src":
        repo_root = parent.parent
        candidates.append(repo_root / "config")

    for cand in candidates:
        defaults = _load_layer_dir(cand, skip_filename=None)
        if defaults["directories"] or defaults["repositories"]:
            return defaults

    return {"directories": {}, "repositories": []}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_config(user_config_path: str) -> Dict[str, Any]:
    """
    Load and merge configuration for pkgmgr.

    Steps:
      1. Determine ~/.config/pkgmgr/ (or dir of user_config_path).
      2. Load all *.yml/*.yaml in that dir (except the user config file) as defaults.
      3. If nothing found, fall back to package defaults.
      4. Load the user config file (if present).
      5. Merge:
         - directories: deep-merge (defaults <- user)
         - repositories: _merge_repo_lists (defaults <- user)
    """
    user_config_path_expanded = os.path.expanduser(user_config_path)
    user_cfg_path = Path(user_config_path_expanded)

    config_dir = user_cfg_path.parent
    if not str(config_dir):
        config_dir = Path(os.path.expanduser("~/.config/pkgmgr"))
    config_dir.mkdir(parents=True, exist_ok=True)

    user_cfg_name = user_cfg_path.name

    # 1+2) Defaults from user directory
    defaults = _load_layer_dir(config_dir, skip_filename=user_cfg_name)

    # 3) Fallback to package defaults
    if not defaults["directories"] and not defaults["repositories"]:
        defaults = _load_defaults_from_package_or_project()

    defaults.setdefault("directories", {})
    defaults.setdefault("repositories", [])

    # 4) User config
    user_cfg: Dict[str, Any] = {}
    if user_cfg_path.is_file():
        user_cfg = _load_yaml_file(user_cfg_path)
    user_cfg.setdefault("directories", {})
    user_cfg.setdefault("repositories", [])

    # 5) Merge
    merged: Dict[str, Any] = {}

    merged["directories"] = {}
    _deep_merge(merged["directories"], defaults["directories"])
    _deep_merge(merged["directories"], user_cfg["directories"])

    merged["repositories"] = []
    _merge_repo_lists(
        merged["repositories"], defaults["repositories"], category_name=None
    )
    _merge_repo_lists(
        merged["repositories"], user_cfg["repositories"], category_name=None
    )

    # Merge other top-level keys
    other_keys = (set(defaults.keys()) | set(user_cfg.keys())) - {
        "directories",
        "repositories",
    }
    for key in other_keys:
        base_val = defaults.get(key)
        override_val = user_cfg.get(key)
        if isinstance(base_val, dict) and isinstance(override_val, dict):
            merged[key] = _deep_merge(dict(base_val), override_val)
        elif override_val is not None:
            merged[key] = override_val
        else:
            merged[key] = base_val

    return merged
