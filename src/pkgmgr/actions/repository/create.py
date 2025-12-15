from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import yaml

from pkgmgr.actions.mirror.io import write_mirrors_file
from pkgmgr.actions.mirror.setup_cmd import setup_mirrors
from pkgmgr.actions.repository.scaffold import render_default_templates
from pkgmgr.core.command.alias import generate_alias
from pkgmgr.core.config.save import save_user_config

Repository = Dict[str, Any]

_NAME_RE = re.compile(r"^[a-z0-9_-]+$")


@dataclass(frozen=True)
class RepoParts:
    host: str
    port: Optional[str]
    owner: str
    name: str


def _run(cmd: str, cwd: str, preview: bool) -> None:
    if preview:
        print(f"[Preview] Would run in {cwd}: {cmd}")
        return
    subprocess.run(cmd, cwd=cwd, shell=True, check=True)


def _git_get(key: str) -> str:
    try:
        out = subprocess.run(
            f"git config --get {key}",
            shell=True,
            check=False,
            capture_output=True,
            text=True,
        )
        return (out.stdout or "").strip()
    except Exception:
        return ""


def _split_host_port(host_with_port: str) -> Tuple[str, Optional[str]]:
    if ":" in host_with_port:
        host, port = host_with_port.split(":", 1)
        return host, port or None
    return host_with_port, None


def _strip_git_suffix(name: str) -> str:
    return name[:-4] if name.endswith(".git") else name


def _parse_git_url(url: str) -> RepoParts:
    if url.startswith("git@") and "://" not in url:
        left, right = url.split(":", 1)
        host = left.split("@", 1)[1]
        path = right.lstrip("/")
        owner, name = path.split("/", 1)
        return RepoParts(host=host, port=None, owner=owner, name=_strip_git_suffix(name))

    parsed = urlparse(url)
    host = (parsed.hostname or "").strip()
    port = str(parsed.port) if parsed.port else None
    path = (parsed.path or "").strip("/")

    if not host or not path or "/" not in path:
        raise ValueError(f"Could not parse git URL: {url}")

    owner, name = path.split("/", 1)
    return RepoParts(host=host, port=port, owner=owner, name=_strip_git_suffix(name))


def _parse_identifier(identifier: str) -> RepoParts:
    ident = identifier.strip()

    if "://" in ident or ident.startswith("git@"):
        return _parse_git_url(ident)

    parts = ident.split("/")
    if len(parts) != 3:
        raise ValueError("Identifier must be URL or 'provider(:port)/owner/repo'.")

    host_with_port, owner, name = parts
    host, port = _split_host_port(host_with_port)
    return RepoParts(host=host, port=port, owner=owner, name=name)


def _ensure_valid_repo_name(name: str) -> None:
    if not name or not _NAME_RE.fullmatch(name):
        raise ValueError("Repository name must match: lowercase a-z, 0-9, '_' and '-'.")


def _repo_homepage(host: str, owner: str, name: str) -> str:
    return f"https://{host}/{owner}/{name}"


def _build_default_primary_url(parts: RepoParts) -> str:
    if parts.port:
        return f"ssh://git@{parts.host}:{parts.port}/{parts.owner}/{parts.name}.git"
    return f"git@{parts.host}:{parts.owner}/{parts.name}.git"


def _write_default_mirrors(repo_dir: str, primary: str, name: str, preview: bool) -> None:
    mirrors = {"origin": primary, "pypi": f"https://pypi.org/project/{name}/"}
    write_mirrors_file(repo_dir, mirrors, preview=preview)


def _git_init_and_initial_commit(repo_dir: str, preview: bool) -> None:
    _run("git init", cwd=repo_dir, preview=preview)
    _run("git add -A", cwd=repo_dir, preview=preview)

    if preview:
        print(f'[Preview] Would run in {repo_dir}: git commit -m "Initial commit"')
        return

    subprocess.run('git commit -m "Initial commit"', cwd=repo_dir, shell=True, check=False)


def _git_push_main_or_master(repo_dir: str, preview: bool) -> None:
    _run("git branch -M main", cwd=repo_dir, preview=preview)
    try:
        _run("git push -u origin main", cwd=repo_dir, preview=preview)
        return
    except subprocess.CalledProcessError:
        pass

    try:
        _run("git branch -M master", cwd=repo_dir, preview=preview)
        _run("git push -u origin master", cwd=repo_dir, preview=preview)
    except subprocess.CalledProcessError as exc:
        print(f"[WARN] Push failed: {exc}")


def create_repo(
    identifier: str,
    config_merged: Dict[str, Any],
    user_config_path: str,
    bin_dir: str,
    *,
    remote: bool = False,
    preview: bool = False,
) -> None:
    parts = _parse_identifier(identifier)
    _ensure_valid_repo_name(parts.name)

    directories = config_merged.get("directories") or {}
    base_dir = os.path.expanduser(str(directories.get("repositories", "~/Repositories")))
    repo_dir = os.path.join(base_dir, parts.host, parts.owner, parts.name)

    author_name = _git_get("user.name") or "Unknown Author"
    author_email = _git_get("user.email") or "unknown@example.invalid"

    homepage = _repo_homepage(parts.host, parts.owner, parts.name)
    primary_url = _build_default_primary_url(parts)

    repositories = config_merged.get("repositories") or []
    exists = any(
        (
            r.get("provider") == parts.host
            and r.get("account") == parts.owner
            and r.get("repository") == parts.name
        )
        for r in repositories
    )

    if not exists:
        new_entry: Repository = {
            "provider": parts.host,
            "port": parts.port,
            "account": parts.owner,
            "repository": parts.name,
            "homepage": homepage,
            "alias": generate_alias(
                {"repository": parts.name, "provider": parts.host, "account": parts.owner},
                bin_dir,
                existing_aliases=set(),
            ),
            "verified": {},
        }

        if os.path.exists(user_config_path):
            with open(user_config_path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}
        else:
            user_config = {"repositories": []}

        user_config.setdefault("repositories", [])
        user_config["repositories"].append(new_entry)

        if preview:
            print(f"[Preview] Would save user config: {user_config_path}")
        else:
            save_user_config(user_config, user_config_path)

        config_merged.setdefault("repositories", []).append(new_entry)
        repo = new_entry
        print(f"[INFO] Added repository to configuration: {parts.host}/{parts.owner}/{parts.name}")
    else:
        repo = next(
            r
            for r in repositories
            if (
                r.get("provider") == parts.host
                and r.get("account") == parts.owner
                and r.get("repository") == parts.name
            )
        )
        print(f"[INFO] Repository already in configuration: {parts.host}/{parts.owner}/{parts.name}")

    if preview:
        print(f"[Preview] Would ensure directory exists: {repo_dir}")
    else:
        os.makedirs(repo_dir, exist_ok=True)

    tpl_context = {
        "provider": parts.host,
        "port": parts.port,
        "account": parts.owner,
        "repository": parts.name,
        "homepage": homepage,
        "author_name": author_name,
        "author_email": author_email,
        "license_text": f"All rights reserved by {author_name}",
        "primary_remote": primary_url,
    }

    render_default_templates(repo_dir, context=tpl_context, preview=preview)
    _git_init_and_initial_commit(repo_dir, preview=preview)

    _write_default_mirrors(repo_dir, primary=primary_url, name=parts.name, preview=preview)

    repo.setdefault("mirrors", {})
    repo["mirrors"].setdefault("origin", primary_url)
    repo["mirrors"].setdefault("pypi", f"https://pypi.org/project/{parts.name}/")

    setup_mirrors(
        selected_repos=[repo],
        repositories_base_dir=base_dir,
        all_repos=config_merged.get("repositories", []),
        preview=preview,
        local=True,
        remote=True,
        ensure_remote=bool(remote),
    )

    if remote:
        _git_push_main_or_master(repo_dir, preview=preview)
