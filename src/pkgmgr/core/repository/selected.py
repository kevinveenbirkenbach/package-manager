#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Sequence

from pkgmgr.core.repository.resolve import resolve_repos
from pkgmgr.core.repository.ignored import filter_ignored

Repository = Dict[str, Any]


def _compile_maybe_regex(pattern: str):
    """
    If pattern is of the form /.../, return a compiled regex (case-insensitive).
    Otherwise return None.
    """
    if len(pattern) >= 2 and pattern.startswith("/") and pattern.endswith("/"):
        try:
            return re.compile(pattern[1:-1], re.IGNORECASE)
        except re.error:
            return None
    return None


def _match_pattern(value: str, pattern: str) -> bool:
    """
    Match a value against a pattern that may be a substring or /regex/.
    """
    if not pattern:
        return True
    regex = _compile_maybe_regex(pattern)
    if regex:
        return bool(regex.search(value))
    return pattern.lower() in value.lower()


def _match_any(values: Sequence[str], pattern: str) -> bool:
    """
    Return True if any of the values matches the pattern.
    """
    for v in values:
        if _match_pattern(v, pattern):
            return True
    return False


def _build_identifier_string(repo: Repository) -> str:
    """
    Build a combined identifier string for string-based filtering.
    """
    provider = str(repo.get("provider", ""))
    account = str(repo.get("account", ""))
    repository = str(repo.get("repository", ""))
    alias = str(repo.get("alias", ""))
    description = str(repo.get("description", ""))
    directory = str(repo.get("directory", ""))

    parts = [
        provider,
        account,
        repository,
        alias,
        f"{provider}/{account}/{repository}",
        description,
        directory,
    ]
    return " ".join(p for p in parts if p)


def _apply_filters(
    repos: List[Repository],
    string_pattern: str,
    category_patterns: List[str],
    tag_patterns: List[str],
) -> List[Repository]:
    if not string_pattern and not category_patterns and not tag_patterns:
        return repos

    filtered: List[Repository] = []

    for repo in repos:
        # String filter
        if string_pattern:
            ident_str = _build_identifier_string(repo)
            if not _match_pattern(ident_str, string_pattern):
                continue

        # Category filter: only real categories, NOT tags
        if category_patterns:
            cats: List[str] = []
            cats.extend(map(str, repo.get("category_files", [])))
            if "category" in repo:
                cats.append(str(repo["category"]))

            if not cats:
                continue

            ok = True
            for pat in category_patterns:
                if not _match_any(cats, pat):
                    ok = False
                    break
            if not ok:
                continue

        # Tag filter: YAML tags only
        if tag_patterns:
            tags: List[str] = list(map(str, repo.get("tags", [])))
            if not tags:
                continue

            ok = True
            for pat in tag_patterns:
                if not _match_any(tags, pat):
                    ok = False
                    break
            if not ok:
                continue

        filtered.append(repo)

    return filtered


def _maybe_filter_ignored(args, repos: List[Repository]) -> List[Repository]:
    """
    Apply ignore filtering unless the caller explicitly opted to include ignored
    repositories (via args.include_ignored).

    Note: this helper is used only for *implicit* selections (all / filters /
    by-directory). For *explicit* identifiers we do NOT filter ignored repos,
    so the user can still target them directly if desired.
    """
    include_ignored: bool = bool(getattr(args, "include_ignored", False))
    if include_ignored:
        return repos
    return filter_ignored(repos)


def get_selected_repos(args, all_repositories: List[Repository]) -> List[Repository]:
    """
    Compute the list of repositories selected by CLI arguments.

    Modes:
      - If identifiers are given: select via resolve_repos() from all_repositories.
        Ignored repositories are *not* filtered here, so explicit identifiers
        always win.
      - Else if any of --category/--string/--tag is used: start from
        all_repositories, apply filters and then drop ignored repos.
      - Else if --all is set: select all_repositories and then drop ignored repos.
      - Else: try to select the repository of the current working directory
        and then drop it if it is ignored.

    The ignore filter can be bypassed by setting args.include_ignored = True
    (e.g. via a CLI flag --include-ignored).
    """
    identifiers: List[str] = getattr(args, "identifiers", []) or []
    use_all: bool = bool(getattr(args, "all", False))
    category_patterns: List[str] = getattr(args, "category", []) or []
    string_pattern: str = getattr(args, "string", "") or ""
    tag_patterns: List[str] = getattr(args, "tag", []) or []

    has_filters = bool(category_patterns or string_pattern or tag_patterns)

    # 1) Explicit identifiers win and bypass ignore filtering
    if identifiers:
        base = resolve_repos(identifiers, all_repositories)
        return _apply_filters(base, string_pattern, category_patterns, tag_patterns)

    # 2) Filter-only mode: start from all repositories
    if has_filters:
        base = _apply_filters(
            list(all_repositories),
            string_pattern,
            category_patterns,
            tag_patterns,
        )
        return _maybe_filter_ignored(args, base)

    # 3) --all (no filters): all repos
    if use_all:
        base = list(all_repositories)
        return _maybe_filter_ignored(args, base)

    # 4) Fallback: try to select repository of current working directory
    cwd = os.path.abspath(os.getcwd())
    by_dir = [
        repo
        for repo in all_repositories
        if os.path.abspath(str(repo.get("directory", ""))) == cwd
    ]
    if by_dir:
        return _maybe_filter_ignored(args, by_dir)

    # No specific match -> empty list
    return []
