from __future__ import annotations

import json
from dataclasses import dataclass, field

from pkgmgr.actions.mirror.url_utils import parse_repo_from_git_url
from pkgmgr.core.credentials.resolver import ResolutionOptions, TokenResolver
from pkgmgr.core.credentials.types import CredentialError
from pkgmgr.core.remote_provisioning.http.client import HttpClient
from pkgmgr.core.remote_provisioning.http.errors import HttpError

GITHUB_HOST = "github.com"
GITHUB_API = "https://api.github.com"
PAGE_SIZE = 100


@dataclass
class ForgeFacts:
    """
    Pull-request and protection facts of every GitHub remote of one repository.

    Attributes:
        merged_heads: head SHA of a merged PR -> PR number.
        open_heads: head branch name of an open PR -> PR number.
        protected: branch names protected on any of the remotes.
        unavailable: why the facts could not be fetched, or None.
    """

    merged_heads: dict[str, int] = field(default_factory=dict)
    open_heads: dict[str, int] = field(default_factory=dict)
    protected: set[str] = field(default_factory=set)
    unavailable: str | None = None


def github_slugs(remote_urls: dict[str, str]) -> list[tuple[str, str]]:
    slugs: list[tuple[str, str]] = []
    for url in remote_urls.values():
        host, owner, name = parse_repo_from_git_url(url)
        if (
            host.lower() == GITHUB_HOST
            and owner
            and name
            and (owner, name) not in slugs
        ):
            slugs.append((owner, name))
    return slugs


def _pages(http: HttpClient, headers: dict[str, str], url: str) -> list[dict]:
    items: list[dict] = []
    page = 1
    while True:
        resp = http.request_json(
            "GET", f"{url}&per_page={PAGE_SIZE}&page={page}", headers=headers
        )
        batch = json.loads(resp.text or "[]")
        items.extend(batch)
        if len(batch) < PAGE_SIZE:
            return items
        page += 1


def fetch_forge_facts(remote_urls: dict[str, str]) -> ForgeFacts:
    facts = ForgeFacts()
    slugs = github_slugs(remote_urls)
    if not slugs:
        return facts

    try:
        token = (
            TokenResolver()
            .get_token(
                "github",
                GITHUB_HOST,
                options=ResolutionOptions(interactive=False, allow_prompt=False),
            )
            .token
        )
    except CredentialError as exc:
        facts.unavailable = f"no GitHub token ({exc})"
        return facts

    http = HttpClient(timeout_s=30)
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "pkgmgr",
    }
    for owner, name in slugs:
        base = f"{GITHUB_API}/repos/{owner}/{name}"
        try:
            for pr in _pages(http, headers, f"{base}/pulls?state=all"):
                if pr["merged_at"]:
                    facts.merged_heads[pr["head"]["sha"]] = pr["number"]
                elif pr["state"] == "open":
                    facts.open_heads[pr["head"]["ref"]] = pr["number"]
            for branch in _pages(http, headers, f"{base}/branches?protected=true"):
                facts.protected.add(branch["name"])
        except (HttpError, ValueError, KeyError, TypeError) as exc:
            facts.unavailable = f"GitHub API failed for {owner}/{name}: {exc}"
            return facts
    return facts
