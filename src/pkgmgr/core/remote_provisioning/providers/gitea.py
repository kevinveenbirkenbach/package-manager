# src/pkgmgr/core/remote_provisioning/providers/gitea.py
from __future__ import annotations

from typing import Any, Dict

from ..http.client import HttpClient
from ..http.errors import HttpError
from ..types import EnsureResult, RepoSpec
from .base import RemoteProvider


class GiteaProvider(RemoteProvider):
    """Gitea provider using Gitea REST API v1."""

    kind = "gitea"

    def __init__(self, timeout_s: int = 15) -> None:
        self._http = HttpClient(timeout_s=timeout_s)

    def can_handle(self, host: str) -> bool:
        """
        Heuristic host match:
        - Acts as a fallback provider for self-hosted setups.
        - Must NOT claim GitHub hosts.
        - If you add more providers later, tighten this heuristic or use provider hints.
        """
        h = host.lower()
        if h in ("github.com", "api.github.com") or h.endswith(".github.com"):
            return False
        return True

    def _headers(self, token: str) -> Dict[str, str]:
        """
        Gitea commonly supports:
          Authorization: token <TOKEN>
        Newer versions may also accept Bearer tokens, but "token" is broadly compatible.
        """
        return {
            "Authorization": f"token {token}",
            "Accept": "application/json",
            "User-Agent": "pkgmgr",
        }

    def repo_exists(self, token: str, spec: RepoSpec) -> bool:
        base = self._api_base(spec.host)
        url = f"{base}/api/v1/repos/{spec.owner}/{spec.name}"
        try:
            resp = self._http.request_json("GET", url, headers=self._headers(token))
            return 200 <= resp.status < 300
        except HttpError as exc:
            if exc.status == 404:
                return False
            raise

    def get_repo_private(self, token: str, spec: RepoSpec) -> bool | None:
        base = self._api_base(spec.host)
        url = f"{base}/api/v1/repos/{spec.owner}/{spec.name}"
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
        base = self._api_base(spec.host)
        url = f"{base}/api/v1/repos/{spec.owner}/{spec.name}"
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
        base = self._api_base(spec.host)

        payload: Dict[str, Any] = {
            "name": spec.name,
            "private": bool(spec.private),
        }
        if spec.description:
            payload["description"] = spec.description
        if spec.default_branch:
            payload["default_branch"] = spec.default_branch

        org_url = f"{base}/api/v1/orgs/{spec.owner}/repos"
        user_url = f"{base}/api/v1/user/repos"

        # Try org first, then fall back to user creation.
        try:
            resp = self._http.request_json(
                "POST",
                org_url,
                headers=self._headers(token),
                payload=payload,
            )
            if 200 <= resp.status < 300:
                html_url = (resp.json or {}).get("html_url") if resp.json else None
                return EnsureResult(
                    status="created",
                    message="Repository created (org).",
                    url=str(html_url) if html_url else None,
                )
        except HttpError:
            # Typical org failures: 404 (not an org), 403 (no rights), 401 (bad token).
            pass

        resp = self._http.request_json(
            "POST",
            user_url,
            headers=self._headers(token),
            payload=payload,
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
