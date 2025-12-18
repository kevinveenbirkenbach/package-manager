#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Load and merge pkgmgr configuration.

Layering rules:

1. Defaults / category files:
   - Zuerst werden alle *.yml/*.yaml (außer config.yaml) im
     Benutzerverzeichnis geladen:
         ~/.config/pkgmgr/

   - Falls dort keine passenden Dateien existieren, wird auf die im
     Paket / Projekt mitgelieferten Config-Verzeichnisse zurückgegriffen:

         <pkg_root>/config_defaults
         <pkg_root>/config
         <project_root>/config_defaults
         <project_root>/config

     Dabei werden ebenfalls alle *.yml/*.yaml als Layer geladen.

   - Der Dateiname ohne Endung (stem) wird als Kategorie-Name
     verwendet und in repo["category_files"] eingetragen.

2. User config:
   - ~/.config/pkgmgr/config.yaml (oder der übergebene Pfad)
     wird geladen und PER LISTEN-MERGE über die Defaults gelegt:
       - directories: dict deep-merge
       - repositories: per _merge_repo_lists (kein Löschen!)

3. Ergebnis:
   - Ein dict mit mindestens:
       config["directories"]  (dict)
       config["repositories"] (list[dict])
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Tuple, Optional

import yaml

Repo = Dict[str, Any]


# ---------------------------------------------------------------------------
# Hilfsfunktionen
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

    - Wenn ein Repo aus new_list noch nicht existiert, wird es hinzugefügt.
    - Wenn es existiert, werden seine Felder per Deep-Merge überschrieben.
    - Wenn category_name gesetzt ist, wird dieser in
      repo["category_files"] eingetragen.
    """
    index: Dict[Tuple[str, str, str], Repo] = {_repo_key(r): r for r in base_list}

    for src in new_list:
        key = _repo_key(src)
        if key == ("", "", ""):
            # Unvollständiger Schlüssel -> einfach anhängen
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

    - skip_filename: Dateiname (z.B. "config.yaml"), der ignoriert
      werden soll (z.B. User-Config).

    Rückgabe:
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
        category_name = path.stem  # Dateiname ohne .yml/.yaml

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
    Fallback: load default configs from various possible install or development
    layouts (pip-installed, editable install, source repo with src/ layout).
    """
    try:
        import pkgmgr  # type: ignore
    except Exception:
        return {"directories": {}, "repositories": []}

    pkg_root = Path(pkgmgr.__file__).resolve().parent
    roots = set()

    # Case 1: installed package (site-packages/pkgmgr)
    roots.add(pkg_root)

    # Case 2: parent directory (site-packages/, src/)
    roots.add(pkg_root.parent)

    # Case 3: src-layout during development:
    #   repo_root/src/pkgmgr -> repo_root
    parent = pkg_root.parent
    if parent.name == "src":
        roots.add(parent.parent)

    # Candidate config dirs
    candidates = []
    for root in roots:
        candidates.append(root / "config_defaults")
        candidates.append(root / "config")

    for cand in candidates:
        defaults = _load_layer_dir(cand, skip_filename=None)
        if defaults["directories"] or defaults["repositories"]:
            return defaults

    return {"directories": {}, "repositories": []}


# ---------------------------------------------------------------------------
# Hauptfunktion
# ---------------------------------------------------------------------------


def load_config(user_config_path: str) -> Dict[str, Any]:
    """
    Load and merge configuration for pkgmgr.

    Schritte:
      1. Ermittle ~/.config/pkgmgr/ (oder das Verzeichnis von user_config_path).
      2. Lade alle *.yml/*.yaml dort (außer der User-Config selbst) als
         Defaults / Kategorie-Layer.
      3. Wenn dort nichts gefunden wurde, Fallback auf Paket/Projekt.
      4. Lade die User-Config-Datei selbst (falls vorhanden).
      5. Merge:
         - directories: deep-merge (Defaults <- User)
         - repositories: _merge_repo_lists (Defaults <- User)
    """
    user_config_path_expanded = os.path.expanduser(user_config_path)
    user_cfg_path = Path(user_config_path_expanded)

    config_dir = user_cfg_path.parent
    if not str(config_dir):
        # Fallback, falls jemand nur "config.yaml" übergibt
        config_dir = Path(os.path.expanduser("~/.config/pkgmgr"))
    config_dir.mkdir(parents=True, exist_ok=True)

    user_cfg_name = user_cfg_path.name

    # 1+2) Defaults / Kategorie-Layer aus dem User-Verzeichnis
    defaults = _load_layer_dir(config_dir, skip_filename=user_cfg_name)

    # 3) Falls dort nichts gefunden wurde, Fallback auf Paket/Projekt
    if not defaults["directories"] and not defaults["repositories"]:
        defaults = _load_defaults_from_package_or_project()

    defaults.setdefault("directories", {})
    defaults.setdefault("repositories", [])

    # 4) User-Config
    user_cfg: Dict[str, Any] = {}
    if user_cfg_path.is_file():
        user_cfg = _load_yaml_file(user_cfg_path)
    user_cfg.setdefault("directories", {})
    user_cfg.setdefault("repositories", [])

    # 5) Merge: directories deep-merge, repositories listen-merge
    merged: Dict[str, Any] = {}

    # directories
    merged["directories"] = {}
    _deep_merge(merged["directories"], defaults["directories"])
    _deep_merge(merged["directories"], user_cfg["directories"])

    # repositories
    merged["repositories"] = []
    _merge_repo_lists(
        merged["repositories"], defaults["repositories"], category_name=None
    )
    _merge_repo_lists(
        merged["repositories"], user_cfg["repositories"], category_name=None
    )

    # andere Top-Level-Keys (falls vorhanden)
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
