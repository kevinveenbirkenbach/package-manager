# src/pkgmgr/core/credentials/resolver.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .providers.env import EnvTokenProvider
from .providers.keyring import KeyringTokenProvider
from .providers.prompt import PromptTokenProvider
from .types import NoCredentialsError, TokenRequest, TokenResult


@dataclass(frozen=True)
class ResolutionOptions:
    """Controls token resolution behavior."""

    interactive: bool = True
    allow_prompt: bool = True
    save_prompt_token_to_keyring: bool = True


class TokenResolver:
    """Resolve tokens from multiple sources (ENV -> Keyring -> Prompt)."""

    def __init__(self) -> None:
        self._env = EnvTokenProvider()
        self._keyring = KeyringTokenProvider()
        self._prompt = PromptTokenProvider()

    def get_token(
        self,
        provider_kind: str,
        host: str,
        owner: Optional[str] = None,
        options: Optional[ResolutionOptions] = None,
    ) -> TokenResult:
        opts = options or ResolutionOptions()
        request = TokenRequest(provider_kind=provider_kind, host=host, owner=owner)

        # 1) ENV
        env_res = self._env.get(request)
        if env_res:
            return env_res

        # 2) Keyring
        try:
            kr_res = self._keyring.get(request)
            if kr_res:
                return kr_res
        except Exception:
            # Keyring missing/unavailable: ignore to allow prompt (workstations)
            # or to fail cleanly below (headless CI without prompt).
            pass

        # 3) Prompt (optional)
        if opts.interactive and opts.allow_prompt:
            prompt_res = self._prompt.get(request)
            if prompt_res:
                if opts.save_prompt_token_to_keyring:
                    try:
                        self._keyring.set(request, prompt_res.token)
                    except Exception:
                        # If keyring cannot store, still use token for this run.
                        pass
                return prompt_res

        raise NoCredentialsError(
            f"No token available for {provider_kind}@{host}"
            + (f" (owner: {owner})" if owner else "")
            + ". Provide it via environment variable or keyring."
        )
