# tests/integration/test_visibility_integration.py
from __future__ import annotations

import io
import os
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

from pkgmgr.actions.mirror.setup_cmd import setup_mirrors
from pkgmgr.actions.mirror.visibility_cmd import set_mirror_visibility
from pkgmgr.core.remote_provisioning.types import RepoSpec


Repository = Dict[str, Any]


class _FakeRegistry:
    """
    Minimal ProviderRegistry-like object for tests.

    - has .providers for provider-hint selection
    - has .resolve(host) to pick a provider
    """

    def __init__(self, provider: Any) -> None:
        self.providers = [provider]
        self._provider = provider

    def resolve(self, host: str) -> Any:
        return self._provider


class FakeProvider:
    """
    Fake remote provider implementing the visibility API surface.

    Key feature: tolerant host matching, because normalize_provider_host()/URL parsing
    may drop ports or schemes.
    """

    kind = "gitea"

    def __init__(self) -> None:
        # maps (host, owner, name) -> private(bool)
        self.privacy: Dict[Tuple[str, str, str], bool] = {}
        self.calls: List[Tuple[str, Any]] = []

    def can_handle(self, host: str) -> bool:
        return True

    def _candidate_hosts(self, host: str) -> List[str]:
        """
        Be tolerant against host normalization differences:
        - may contain scheme (https://...)
        - may contain port (host:2201)
        """
        h = (host or "").strip()
        if not h:
            return [h]

        candidates = [h]

        # strip scheme if present
        if h.startswith("http://"):
            candidates.append(h[len("http://") :])
        if h.startswith("https://"):
            candidates.append(h[len("https://") :])

        # strip port if present (host:port)
        for c in list(candidates):
            if ":" in c:
                candidates.append(c.split(":", 1)[0])

        # de-dup
        out: List[str] = []
        for c in candidates:
            if c not in out:
                out.append(c)
        return out

    def repo_exists(self, token: str, spec: RepoSpec) -> bool:
        self.calls.append(("repo_exists", (token, spec)))
        for h in self._candidate_hosts(spec.host):
            if (h, spec.owner, spec.name) in self.privacy:
                return True
        return False

    def create_repo(self, token: str, spec: RepoSpec):
        self.calls.append(("create_repo", (token, spec)))
        # store under the provided host (as-is)
        self.privacy[(spec.host, spec.owner, spec.name)] = bool(spec.private)
        return types.SimpleNamespace(status="created", message="created", url=None)

    def get_repo_private(self, token: str, spec: RepoSpec) -> Optional[bool]:
        self.calls.append(("get_repo_private", (token, spec)))
        for h in self._candidate_hosts(spec.host):
            key = (h, spec.owner, spec.name)
            if key in self.privacy:
                return self.privacy[key]
        return None

    def set_repo_private(self, token: str, spec: RepoSpec, *, private: bool) -> None:
        self.calls.append(("set_repo_private", (token, spec, private)))
        # update whichever key exists; else create on spec.host
        for h in self._candidate_hosts(spec.host):
            key = (h, spec.owner, spec.name)
            if key in self.privacy:
                self.privacy[key] = bool(private)
                return
        self.privacy[(spec.host, spec.owner, spec.name)] = bool(private)


def _mk_ctx(*, identifier: str, repo_dir: str, mirrors: Dict[str, str]) -> Any:
    return types.SimpleNamespace(
        identifier=identifier,
        repo_dir=repo_dir,
        resolved_mirrors=mirrors,
    )


class TestMirrorVisibilityIntegration(unittest.TestCase):
    """
    Integration tests for:
      - pkgmgr.actions.mirror.visibility_cmd.set_mirror_visibility
      - pkgmgr.actions.mirror.setup_cmd.setup_mirrors (ensure_visibility semantics)
    """

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _repo_dir(self, name: str) -> str:
        d = os.path.join(self.tmp.name, name)
        os.makedirs(d, exist_ok=True)
        return d

    @patch("pkgmgr.core.credentials.resolver.TokenResolver.get_token")
    @patch("pkgmgr.core.remote_provisioning.visibility.ProviderRegistry.default")
    @patch("pkgmgr.actions.mirror.visibility_cmd.build_context")
    def test_mirror_visibility_applies_to_all_git_mirrors_updated_and_noop(
        self,
        m_build_context,
        m_registry_default,
        m_get_token,
    ) -> None:
        """
        Scenario:
          - repo has two git mirrors
          - one mirror needs update -> UPDATED
          - second mirror already desired -> NOOP
        """
        provider = FakeProvider()
        registry = _FakeRegistry(provider)
        m_registry_default.return_value = registry

        # Avoid interactive token prompt
        m_get_token.return_value = types.SimpleNamespace(token="test-token")

        # Seed provider state:
        # - repo1 currently private=True
        # - We'll set visibility to public -> should UPDATE
        provider.privacy[("git.veen.world", "me", "repo1")] = True

        repo = {"id": "repo1", "description": "Repo 1"}
        repo_dir = self._repo_dir("repo1")

        m_build_context.return_value = _mk_ctx(
            identifier="repo1",
            repo_dir=repo_dir,
            mirrors={
                "origin": "ssh://git.veen.world:2201/me/repo1.git",
                "backup": "https://git.veen.world:2201/me/repo1.git",
            },
        )

        buf = io.StringIO()
        with redirect_stdout(buf):
            set_mirror_visibility(
                selected_repos=[repo],
                repositories_base_dir=self.tmp.name,
                all_repos=[repo],
                visibility="public",
                preview=False,
            )
        out = buf.getvalue()

        # We apply to BOTH git mirrors.
        self.assertIn("[MIRROR VISIBILITY] applying to mirror 'origin':", out)
        self.assertIn("[MIRROR VISIBILITY] applying to mirror 'backup':", out)

        # After first update, second call will see it already public (NOOP).
        self.assertIn("[REMOTE VISIBILITY] UPDATED:", out)
        self.assertIn("[REMOTE VISIBILITY] NOOP:", out)

        # Final state must be public (private=False)
        self.assertFalse(provider.privacy[("git.veen.world", "me", "repo1")])

    @patch("pkgmgr.core.credentials.resolver.TokenResolver.get_token")
    @patch("pkgmgr.core.remote_provisioning.visibility.ProviderRegistry.default")
    @patch("pkgmgr.actions.mirror.visibility_cmd.build_context")
    @patch("pkgmgr.actions.mirror.visibility_cmd.determine_primary_remote_url")
    def test_mirror_visibility_fallback_to_primary_when_no_git_mirrors(
        self,
        m_determine_primary,
        m_build_context,
        m_registry_default,
        m_get_token,
    ) -> None:
        """
        Scenario:
          - no git mirrors in MIRRORS config
          - we fall back to primary URL and apply visibility there
        """
        provider = FakeProvider()
        registry = _FakeRegistry(provider)
        m_registry_default.return_value = registry
        m_get_token.return_value = types.SimpleNamespace(token="test-token")

        # Seed state: currently public (private=False), target private -> UPDATED
        provider.privacy[("git.veen.world", "me", "repo2")] = False

        repo = {"id": "repo2", "description": "Repo 2"}
        repo_dir = self._repo_dir("repo2")

        m_build_context.return_value = _mk_ctx(
            identifier="repo2",
            repo_dir=repo_dir,
            mirrors={
                # non-git mirror entries
                "pypi": "https://pypi.org/project/example/",
            },
        )
        m_determine_primary.return_value = "ssh://git.veen.world:2201/me/repo2.git"

        buf = io.StringIO()
        with redirect_stdout(buf):
            set_mirror_visibility(
                selected_repos=[repo],
                repositories_base_dir=self.tmp.name,
                all_repos=[repo],
                visibility="private",
                preview=False,
            )
        out = buf.getvalue()

        self.assertIn("[MIRROR VISIBILITY] applying to primary:", out)
        self.assertIn("[REMOTE VISIBILITY] UPDATED:", out)
        self.assertTrue(provider.privacy[("git.veen.world", "me", "repo2")])

    @patch("pkgmgr.actions.mirror.setup_cmd.probe_remote_reachable_detail")
    @patch("pkgmgr.actions.mirror.setup_cmd.ensure_remote_repository_for_url")
    @patch("pkgmgr.core.credentials.resolver.TokenResolver.get_token")
    @patch("pkgmgr.core.remote_provisioning.visibility.ProviderRegistry.default")
    @patch("pkgmgr.actions.mirror.setup_cmd.build_context")
    def test_setup_mirrors_provision_public_enforces_visibility_and_private_default(
        self,
        m_build_context,
        m_registry_default,
        m_get_token,
        m_ensure_remote_for_url,
        m_probe,
    ) -> None:
        """
        Covers the "mirror provision --public" semantics:
          - setup_mirrors(remote=True, ensure_remote=True, ensure_visibility="public")
          - ensure_remote_repository_for_url is called with private_default=False
          - then set_repo_visibility is applied (UPDATED/NOOP depending on current state)
          - git probing is mocked (no subprocess)
        """
        provider = FakeProvider()
        registry = _FakeRegistry(provider)
        m_registry_default.return_value = registry
        m_get_token.return_value = types.SimpleNamespace(token="test-token")

        # Make git probing always OK (no subprocess calls)
        m_probe.return_value = (True, "")

        # Seed provider: repo4 currently private=True, target public -> UPDATED
        provider.privacy[("git.veen.world", "me", "repo4")] = True

        repo = {"id": "repo4", "description": "Repo 4", "private": True}
        repo_dir = self._repo_dir("repo4")

        m_build_context.return_value = _mk_ctx(
            identifier="repo4",
            repo_dir=repo_dir,
            mirrors={
                "origin": "ssh://git.veen.world:2201/me/repo4.git",
            },
        )

        buf = io.StringIO()
        with redirect_stdout(buf):
            setup_mirrors(
                selected_repos=[repo],
                repositories_base_dir=self.tmp.name,
                all_repos=[repo],
                preview=False,
                local=False,
                remote=True,
                ensure_remote=True,
                ensure_visibility="public",
            )
        out = buf.getvalue()

        # ensure_remote_repository_for_url called and private_default overridden to False
        self.assertTrue(m_ensure_remote_for_url.called)
        _, kwargs = m_ensure_remote_for_url.call_args
        self.assertIn("private_default", kwargs)
        self.assertFalse(kwargs["private_default"])

        # Visibility should be enforced
        self.assertIn("[REMOTE VISIBILITY] UPDATED:", out)
        self.assertFalse(provider.privacy[("git.veen.world", "me", "repo4")])


if __name__ == "__main__":
    unittest.main()
