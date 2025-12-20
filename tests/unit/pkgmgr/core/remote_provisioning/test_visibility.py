# tests/unit/pkgmgr/core/remote_provisioning/test_visibility.py
from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from pkgmgr.core.remote_provisioning.types import (
    AuthError,
    NetworkError,
    PermissionError,
    ProviderHint,
    RepoSpec,
    UnsupportedProviderError,
)
from pkgmgr.core.remote_provisioning.visibility import (
    VisibilityOptions,
    set_repo_visibility,
)
from pkgmgr.core.remote_provisioning.http.errors import HttpError


class TestSetRepoVisibility(unittest.TestCase):
    def _mk_provider(self, *, kind: str = "gitea") -> MagicMock:
        p = MagicMock()
        p.kind = kind
        return p

    def _mk_registry(
        self, provider: MagicMock | None, providers: list[MagicMock] | None = None
    ) -> MagicMock:
        reg = MagicMock()
        reg.resolve.return_value = provider
        reg.providers = (
            providers
            if providers is not None
            else ([provider] if provider is not None else [])
        )
        return reg

    def _mk_token_resolver(self, token: str = "TOKEN") -> MagicMock:
        resolver = MagicMock()
        tok = MagicMock()
        tok.token = token
        resolver.get_token.return_value = tok
        return resolver

    def test_preview_returns_skipped_and_does_not_call_provider(self) -> None:
        provider = self._mk_provider()
        reg = self._mk_registry(provider)
        resolver = self._mk_token_resolver()

        spec = RepoSpec(host="git.veen.world", owner="me", name="repo", private=True)

        res = set_repo_visibility(
            spec,
            private=False,
            options=VisibilityOptions(preview=True),
            registry=reg,
            token_resolver=resolver,
        )

        self.assertEqual(res.status, "skipped")
        provider.get_repo_private.assert_not_called()
        provider.set_repo_private.assert_not_called()

    def test_unsupported_provider_raises(self) -> None:
        reg = self._mk_registry(provider=None, providers=[])

        spec = RepoSpec(host="unknown.host", owner="me", name="repo", private=True)

        with self.assertRaises(UnsupportedProviderError):
            set_repo_visibility(
                spec,
                private=True,
                registry=reg,
                token_resolver=self._mk_token_resolver(),
            )

    def test_notfound_when_provider_returns_none(self) -> None:
        provider = self._mk_provider()
        provider.get_repo_private.return_value = None

        reg = self._mk_registry(provider)
        resolver = self._mk_token_resolver()

        spec = RepoSpec(host="git.veen.world", owner="me", name="repo", private=True)

        res = set_repo_visibility(
            spec,
            private=True,
            registry=reg,
            token_resolver=resolver,
        )

        self.assertEqual(res.status, "notfound")
        provider.set_repo_private.assert_not_called()

    def test_noop_when_already_desired(self) -> None:
        provider = self._mk_provider()
        provider.get_repo_private.return_value = True

        reg = self._mk_registry(provider)
        resolver = self._mk_token_resolver()

        spec = RepoSpec(host="git.veen.world", owner="me", name="repo", private=True)

        res = set_repo_visibility(
            spec,
            private=True,
            registry=reg,
            token_resolver=resolver,
        )

        self.assertEqual(res.status, "noop")
        provider.set_repo_private.assert_not_called()

    def test_updated_when_needs_change(self) -> None:
        provider = self._mk_provider()
        provider.get_repo_private.return_value = True

        reg = self._mk_registry(provider)
        resolver = self._mk_token_resolver()

        spec = RepoSpec(host="git.veen.world", owner="me", name="repo", private=True)

        res = set_repo_visibility(
            spec,
            private=False,
            registry=reg,
            token_resolver=resolver,
        )

        self.assertEqual(res.status, "updated")
        provider.set_repo_private.assert_called_once()
        args, kwargs = provider.set_repo_private.call_args
        self.assertEqual(kwargs.get("private"), False)

    def test_provider_hint_overrides_registry_resolution(self) -> None:
        # registry.resolve returns gitea provider, but hint forces github provider
        gitea = self._mk_provider(kind="gitea")
        github = self._mk_provider(kind="github")
        github.get_repo_private.return_value = True

        reg = self._mk_registry(gitea, providers=[gitea, github])
        resolver = self._mk_token_resolver()

        spec = RepoSpec(host="github.com", owner="me", name="repo", private=True)

        res = set_repo_visibility(
            spec,
            private=False,
            provider_hint=ProviderHint(kind="github"),
            registry=reg,
            token_resolver=resolver,
        )

        self.assertEqual(res.status, "updated")
        github.get_repo_private.assert_called_once()
        gitea.get_repo_private.assert_not_called()

    def test_http_error_401_maps_to_auth_error(self) -> None:
        provider = self._mk_provider()
        provider.get_repo_private.side_effect = HttpError(
            status=401, message="nope", body=""
        )

        reg = self._mk_registry(provider)
        resolver = self._mk_token_resolver()

        spec = RepoSpec(host="git.veen.world", owner="me", name="repo", private=True)

        with self.assertRaises(AuthError):
            set_repo_visibility(
                spec, private=True, registry=reg, token_resolver=resolver
            )

    def test_http_error_403_maps_to_permission_error(self) -> None:
        provider = self._mk_provider()
        provider.get_repo_private.side_effect = HttpError(
            status=403, message="nope", body=""
        )

        reg = self._mk_registry(provider)
        resolver = self._mk_token_resolver()

        spec = RepoSpec(host="git.veen.world", owner="me", name="repo", private=True)

        with self.assertRaises(PermissionError):
            set_repo_visibility(
                spec, private=True, registry=reg, token_resolver=resolver
            )

    def test_http_error_status_0_maps_to_network_error(self) -> None:
        provider = self._mk_provider()
        provider.get_repo_private.side_effect = HttpError(
            status=0, message="connection failed", body=""
        )

        reg = self._mk_registry(provider)
        resolver = self._mk_token_resolver()

        spec = RepoSpec(host="git.veen.world", owner="me", name="repo", private=True)

        with self.assertRaises(NetworkError):
            set_repo_visibility(
                spec, private=True, registry=reg, token_resolver=resolver
            )

    def test_http_error_other_maps_to_network_error(self) -> None:
        provider = self._mk_provider()
        provider.get_repo_private.side_effect = HttpError(
            status=500, message="boom", body="server error"
        )

        reg = self._mk_registry(provider)
        resolver = self._mk_token_resolver()

        spec = RepoSpec(host="git.veen.world", owner="me", name="repo", private=True)

        with self.assertRaises(NetworkError):
            set_repo_visibility(
                spec, private=True, registry=reg, token_resolver=resolver
            )


if __name__ == "__main__":
    unittest.main()
