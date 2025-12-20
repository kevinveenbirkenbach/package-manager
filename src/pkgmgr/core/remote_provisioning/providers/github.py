# src/pkgmgr/core/remote_provisioning/providers/github.py
from __future__ import annotations

from typing import Any, Dict

from ..http.client import HttpClient
from ..http.errors import HttpError
from ..types import EnsureResult, RepoSpec
from .base import RemoteProvider


class GitHubProvider(RemoteProvider):
    """GitHub provider using GitHub REST API."""

    kind = "github"

    def __init__(self, timeout_s: int = 15) -> None:
        self._http = HttpClient(timeout_s=timeout_s)

    def can_handle(self, host: str) -> bool:
        h = host.lower()
        return h in ("github.com", "api.github.com") or h.endswith(".github.com")

    def _api_base(self, host: str) -> str:
        """
        GitHub API base:
        - Public GitHub: https://api.github.com
        - GitHub Enterprise Server: https://<host>/api/v3
        """
        h = host.lower()
        if h in ("github.com", "api.github.com"):
            return "https://api.github.com"

        # Enterprise instance:
        if host.startswith("http://") or host.startswith("https://"):
            return host.rstrip("/") + "/api/v3"
        return f"https://{host}/api/v3"

    def _headers(self, token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "pkgmgr",
        }

    def repo_exists(self, token: str, spec: RepoSpec) -> bool:
        api = self._api_base(spec.host)
        url = f"{api}/repos/{spec.owner}/{spec.name}"
        try:
            resp = self._http.request_json("GET", url, headers=self._headers(token))
            return 200 <= resp.status < 300
        except HttpError as exc:
            if exc.status == 404:
                return False
            raise

    def get_repo_private(self, token: str, spec: RepoSpec) -> bool | None:
        api = self._api_base(spec.host)
        url = f"{api}/repos/{spec.owner}/{spec.name}"
        try:
            resp = self._http.request_json("GET", url, headers=self._headers(token))
        except HttpError as exc:
            if exc.status == 404:
                return None
            raise

        if not (200 <= resp.status < 300):
            return None
        data = resp.json or {}
        return bool(data.get("private", False))

    def set_repo_private(self, token: str, spec: RepoSpec, *, private: bool) -> None:
        api = self._api_base(spec.host)
        url = f"{api}/repos/{spec.owner}/{spec.name}"
        payload: Dict[str, Any] = {"private": bool(private)}

        resp = self._http.request_json(
            "PATCH",
            url,
            headers=self._headers(token),
            payload=payload,
        )
        if not (200 <= resp.status < 300):
            raise HttpError(
                status=resp.status,
                message="Failed to update repository.",
                body=resp.text,
            )

    def create_repo(self, token: str, spec: RepoSpec) -> EnsureResult:
        api = self._api_base(spec.host)

        payload: Dict[str, Any] = {
            "name": spec.name,
            "private": bool(spec.private),
        }
        if spec.description:
            payload["description"] = spec.description
        if spec.default_branch:
            payload["default_branch"] = spec.default_branch

        org_url = f"{api}/orgs/{spec.owner}/repos"
        user_url = f"{api}/user/repos"

        # Try org first, then fall back to user creation.
        try:
            resp = self._http.request_json(
                "POST", org_url, headers=self._headers(token), payload=payload
            )
            if 200 <= resp.status < 300:
                html_url = (resp.json or {}).get("html_url") if resp.json else None
                return EnsureResult(
                    status="created",
                    message="Repository created (org).",
                    url=str(html_url) if html_url else None,
                )
        except HttpError:
            pass

        resp = self._http.request_json(
            "POST", user_url, headers=self._headers(token), payload=payload
        )
        if 200 <= resp.status < 300:
            html_url = (resp.json or {}).get("html_url") if resp.json else None
            return EnsureResult(
                status="created",
                message="Repository created (user).",
                url=str(html_url) if html_url else None,
            )

        return EnsureResult(
            status="failed",
            message=f"Failed to create repository (status {resp.status}).",
        )
