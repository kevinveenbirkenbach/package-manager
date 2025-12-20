# src/pkgmgr/core/remote_provisioning/visibility.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pkgmgr.core.credentials.resolver import ResolutionOptions, TokenResolver

from .http.errors import HttpError
from .registry import ProviderRegistry
from .types import (
    AuthError,
    EnsureResult,
    NetworkError,
    PermissionError,
    ProviderHint,
    RepoSpec,
    UnsupportedProviderError,
)


@dataclass(frozen=True)
class VisibilityOptions:
    """Options controlling remote visibility updates."""

    preview: bool = False
    interactive: bool = True
    allow_prompt: bool = True
    save_prompt_token_to_keyring: bool = True


def _raise_mapped_http_error(exc: HttpError, host: str) -> None:
    """Map HttpError into domain-specific error types."""
    if exc.status == 0:
        raise NetworkError(f"Network error while talking to {host}: {exc}") from exc
    if exc.status == 401:
        raise AuthError(f"Authentication failed for {host} (401).") from exc
    if exc.status == 403:
        raise PermissionError(f"Permission denied for {host} (403).") from exc

    raise NetworkError(
        f"HTTP error from {host}: status={exc.status}, message={exc}, body={exc.body}"
    ) from exc


def set_repo_visibility(
    spec: RepoSpec,
    *,
    private: bool,
    provider_hint: Optional[ProviderHint] = None,
    options: Optional[VisibilityOptions] = None,
    registry: Optional[ProviderRegistry] = None,
    token_resolver: Optional[TokenResolver] = None,
) -> EnsureResult:
    """
    Set repository visibility (public/private) WITHOUT creating repositories.

    Behavior:
      - If repo does not exist -> status=notfound
      - If already desired -> status=noop
      - If changed -> status=updated
      - Respects preview mode -> status=skipped
      - Maps HTTP errors to domain-specific errors
    """
    opts = options or VisibilityOptions()
    reg = registry or ProviderRegistry.default()
    resolver = token_resolver or TokenResolver()

    provider = reg.resolve(spec.host)
    if provider_hint and provider_hint.kind:
        forced = provider_hint.kind.strip().lower()
        forced_provider = next(
            (p for p in reg.providers if getattr(p, "kind", "").lower() == forced),
            None,
        )
        if forced_provider is not None:
            provider = forced_provider

    if provider is None:
        raise UnsupportedProviderError(f"No provider matched host: {spec.host}")

    token_opts = ResolutionOptions(
        interactive=opts.interactive,
        allow_prompt=opts.allow_prompt,
        save_prompt_token_to_keyring=opts.save_prompt_token_to_keyring,
    )
    token = resolver.get_token(
        provider_kind=getattr(provider, "kind", "unknown"),
        host=spec.host,
        owner=spec.owner,
        options=token_opts,
    )

    if opts.preview:
        return EnsureResult(
            status="skipped",
            message="Preview mode: no remote changes performed.",
        )

    try:
        current_private = provider.get_repo_private(token.token, spec)
        if current_private is None:
            return EnsureResult(status="notfound", message="Repository not found.")

        if bool(current_private) == bool(private):
            return EnsureResult(
                status="noop",
                message=f"Repository already {'private' if private else 'public'}.",
            )

        provider.set_repo_private(token.token, spec, private=private)
        return EnsureResult(
            status="updated",
            message=f"Visibility updated to {'private' if private else 'public'}.",
        )
    except HttpError as exc:
        _raise_mapped_http_error(exc, host=spec.host)
        return EnsureResult(status="failed", message="Unreachable error mapping.")
