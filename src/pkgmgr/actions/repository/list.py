#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pretty-print repository list with status, categories, tags and path.

- Tags come exclusively from YAML: repo["tags"].
- Categories come from repo["category_files"] (YAML file names without
  .yml/.yaml) and optional repo["category"].
- Optional detail mode (--description) prints an extended section per
  repository with description, homepage, etc.
"""

from __future__ import annotations

import os
import re
from textwrap import wrap
from typing import Any, Dict, List, Optional

Repository = Dict[str, Any]

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
GREY = "\033[90m"


def _compile_maybe_regex(pattern: str) -> Optional[re.Pattern[str]]:
    """
    If pattern is of the form /.../, return a compiled regex (case-insensitive).
    Otherwise return None.
    """
    if not pattern:
        return None
    if len(pattern) >= 2 and pattern.startswith("/") and pattern.endswith("/"):
        try:
            return re.compile(pattern[1:-1], re.IGNORECASE)
        except re.error:
            return None
    return None


def _status_matches(status: str, status_filter: str) -> bool:
    """
    Match a status string against an optional filter (substring or /regex/).
    """
    if not status_filter:
        return True

    regex = _compile_maybe_regex(status_filter)
    if regex:
        return bool(regex.search(status))
    return status_filter.lower() in status.lower()


def _compute_repo_dir(repositories_base_dir: str, repo: Repository) -> str:
    """
    Compute the local directory for a repository.

    If the repository already has a 'directory' key, that is used;
    otherwise the path is constructed from provider/account/repository
    under repositories_base_dir.
    """
    if repo.get("directory"):
        return os.path.expanduser(str(repo["directory"]))

    provider = str(repo.get("provider", ""))
    account = str(repo.get("account", ""))
    repository = str(repo.get("repository", ""))

    return os.path.join(
        os.path.expanduser(repositories_base_dir),
        provider,
        account,
        repository,
    )


def _compute_status(
    repo: Repository,
    repo_dir: str,
    binaries_dir: str,
) -> str:
    """
    Compute a human-readable status string, e.g. 'present,alias,ignored'.
    """
    parts: List[str] = []

    exists = os.path.isdir(repo_dir)
    if exists:
        parts.append("present")
    else:
        parts.append("absent")

    alias = repo.get("alias")
    if alias:
        alias_path = os.path.join(os.path.expanduser(binaries_dir), str(alias))
        if os.path.exists(alias_path):
            parts.append("alias")
        else:
            parts.append("alias-missing")

    if repo.get("ignore"):
        parts.append("ignored")

    return ",".join(parts) if parts else "-"


def _color_status(status_padded: str) -> str:
    """
    Color individual status flags inside a padded status string.

    Input is expected to be right-padded to the column width.

    Color mapping:
      - present        -> green
      - absent         -> red
      - alias          -> red
      - alias-missing  -> red
      - ignored        -> magenta
      - other          -> default
    """
    core = status_padded.rstrip()
    pad_spaces = len(status_padded) - len(core)

    plain_parts = core.split(",") if core else []
    colored_parts: List[str] = []

    for raw_part in plain_parts:
        name = raw_part.strip()
        if not name:
            continue

        if name == "present":
            color = GREEN
        elif name == "absent":
            color = MAGENTA
        elif name in ("alias", "alias-missing"):
            color = YELLOW
        elif name == "ignored":
            color = MAGENTA
        else:
            color = ""

        if color:
            colored_parts.append(f"{color}{name}{RESET}")
        else:
            colored_parts.append(name)

    colored_core = ",".join(colored_parts)
    return colored_core + (" " * pad_spaces)


def list_repositories(
    repositories: List[Repository],
    repositories_base_dir: str,
    binaries_dir: str,
    search_filter: str = "",
    status_filter: str = "",
    extra_tags: Optional[List[str]] = None,
    show_description: bool = False,
) -> None:
    """
    Print a table of repositories and (optionally) detailed descriptions.

    Parameters
    ----------
    repositories:
        Repositories to show (usually already filtered by get_selected_repos).
    repositories_base_dir:
        Base directory where repositories live.
    binaries_dir:
        Directory where alias symlinks live.
    search_filter:
        Optional substring/regex filter on identifier and metadata.
    status_filter:
        Optional filter on computed status.
    extra_tags:
        Additional tags to show for each repository (CLI overlay only).
    show_description:
        If True, print a detailed block for each repository after the table.
    """
    if extra_tags is None:
        extra_tags = []

    search_regex = _compile_maybe_regex(search_filter)
    rows: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Build rows
    # ------------------------------------------------------------------
    for repo in repositories:
        identifier = str(repo.get("repository") or repo.get("alias") or "")
        alias = str(repo.get("alias") or "")
        provider = str(repo.get("provider") or "")
        account = str(repo.get("account") or "")
        description = str(repo.get("description") or "")
        homepage = str(repo.get("homepage") or "")

        repo_dir = _compute_repo_dir(repositories_base_dir, repo)
        status = _compute_status(repo, repo_dir, binaries_dir)

        if not _status_matches(status, status_filter):
            continue

        if search_filter:
            haystack = " ".join(
                [
                    identifier,
                    alias,
                    provider,
                    account,
                    description,
                    homepage,
                    repo_dir,
                ]
            )
            if search_regex:
                if not search_regex.search(haystack):
                    continue
            else:
                if search_filter.lower() not in haystack.lower():
                    continue

        categories: List[str] = []
        categories.extend(map(str, repo.get("category_files", [])))
        if repo.get("category"):
            categories.append(str(repo["category"]))

        yaml_tags: List[str] = list(map(str, repo.get("tags", [])))
        display_tags: List[str] = sorted(set(yaml_tags + list(map(str, extra_tags))))

        rows.append(
            {
                "repo": repo,
                "identifier": identifier,
                "status": status,
                "categories": categories,
                "tags": display_tags,
                "dir": repo_dir,
            }
        )

    if not rows:
        print("No repositories matched the given filters.")
        return

    # ------------------------------------------------------------------
    # Table section (header grey, values white, per-flag colored status)
    # ------------------------------------------------------------------
    ident_width = max(len("IDENTIFIER"), max(len(r["identifier"]) for r in rows))
    status_width = max(len("STATUS"), max(len(r["status"]) for r in rows))
    cat_width = max(
        len("CATEGORIES"),
        max((len(",".join(r["categories"])) for r in rows), default=0),
    )
    tag_width = max(
        len("TAGS"),
        max((len(",".join(r["tags"])) for r in rows), default=0),
    )

    header = (
        f"{GREY}{BOLD}"
        f"{'IDENTIFIER'.ljust(ident_width)}  "
        f"{'STATUS'.ljust(status_width)}  "
        f"{'CATEGORIES'.ljust(cat_width)}  "
        f"{'TAGS'.ljust(tag_width)}  "
        "DIR"
        f"{RESET}"
    )
    print(header)
    print("-" * (ident_width + status_width + cat_width + tag_width + 10 + 40))

    for r in rows:
        ident_col = r["identifier"].ljust(ident_width)
        cat_col = ",".join(r["categories"]).ljust(cat_width)
        tag_col = ",".join(r["tags"]).ljust(tag_width)
        dir_col = r["dir"]
        status = r["status"]

        status_padded = status.ljust(status_width)
        status_colored = _color_status(status_padded)

        print(f"{ident_col}  {status_colored}  {cat_col}  {tag_col}  {dir_col}")

    # ------------------------------------------------------------------
    # Detailed section (alias value red, same status coloring)
    # ------------------------------------------------------------------
    if not show_description:
        return

    print()
    print(f"{BOLD}Detailed repository information:{RESET}")
    print()

    for r in rows:
        repo = r["repo"]
        identifier = r["identifier"]
        alias = str(repo.get("alias") or "")
        provider = str(repo.get("provider") or "")
        account = str(repo.get("account") or "")
        repository = str(repo.get("repository") or "")
        description = str(repo.get("description") or "")
        homepage = str(repo.get("homepage") or "")
        categories = r["categories"]
        tags = r["tags"]
        repo_dir = r["dir"]
        status = r["status"]

        print(f"{BOLD}{identifier}{RESET}")

        print(f"  Provider:   {provider}")
        print(f"  Account:    {account}")
        print(f"  Repository: {repository}")

        # Alias value highlighted in red
        if alias:
            print(f"  Alias:      {RED}{alias}{RESET}")

        status_colored = _color_status(status)
        print(f"  Status:     {status_colored}")

        if categories:
            print(f"  Categories: {', '.join(categories)}")

        if tags:
            print(f"  Tags:       {', '.join(tags)}")

        print(f"  Directory:  {repo_dir}")

        if homepage:
            print(f"  Homepage:   {homepage}")

        if description:
            print("  Description:")
            for line in wrap(description, width=78):
                print(f"    {line}")

        print()
