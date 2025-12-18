# src/pkgmgr/core/credentials/resolver.py
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional

from .providers.env import EnvTokenProvider
from .providers.gh import GhTokenProvider
from .providers.keyring import KeyringTokenProvider
from .providers.prompt import PromptTokenProvider
from .types import (
    KeyringUnavailableError,
    NoCredentialsError,
    TokenRequest,
    TokenResult,
)
from .validate import validate_token


@dataclass(frozen=True)
class ResolutionOptions:
    """Controls token resolution behavior."""

    interactive: bool = True
    allow_prompt: bool = True
    save_prompt_token_to_keyring: bool = True


class TokenResolver:
    """
    Resolve tokens for provider APIs using the following policy:

    0) ENV (explicit user intent) -> return as-is (do NOT persist)
    1) GitHub CLI (gh)            -> if available and token validates, return
    2) Keyring                    -> if token validates, return; if invalid and
                                    interactive prompting is allowed, prompt and
                                    OVERWRITE the keyring entry
    3) Prompt                     -> prompt and (optionally) store in keyring

    Notes:
    - Keyring requires python-keyring.
    - Token validation is provider-specific (currently GitHub cloud).
    """

    def __init__(self) -> None:
        self._env = EnvTokenProvider()
        self._gh = GhTokenProvider()
        self._keyring = KeyringTokenProvider()
        self._prompt = PromptTokenProvider()
        self._warned_keyring: bool = False

    def _warn_keyring_unavailable(self, exc: Exception) -> None:
        if self._warned_keyring:
            return
        self._warned_keyring = True

        msg = str(exc).strip() or "Keyring is unavailable."
        print("[WARN] Keyring support is not available.", file=sys.stderr)
        print(f"       {msg}", file=sys.stderr)
        print("       Tokens will NOT be persisted securely.", file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "       To enable secure token storage, install python-keyring:",
            file=sys.stderr,
        )
        print("         pip install keyring", file=sys.stderr)
        print("", file=sys.stderr)
        print("       Or install via system packages:", file=sys.stderr)
        print("         sudo apt install python3-keyring", file=sys.stderr)
        print("         sudo pacman -S python-keyring", file=sys.stderr)
        print("         sudo dnf install python3-keyring", file=sys.stderr)
        print("", file=sys.stderr)

    def _prompt_and_maybe_store(
        self,
        request: TokenRequest,
        opts: ResolutionOptions,
    ) -> Optional[TokenResult]:
        """
        Prompt for a token and optionally store it in keyring.
        If keyring is unavailable, still return the token for this run.
        """
        if not (opts.interactive and opts.allow_prompt):
            return None

        prompt_res = self._prompt.get(request)
        if not prompt_res:
            return None

        if opts.save_prompt_token_to_keyring:
            try:
                self._keyring.set(request, prompt_res.token)  # overwrite is fine
            except KeyringUnavailableError as exc:
                self._warn_keyring_unavailable(exc)
            except Exception:
                # If keyring cannot store, still use token for this run.
                pass

        return prompt_res

    def get_token(
        self,
        provider_kind: str,
        host: str,
        owner: Optional[str] = None,
        options: Optional[ResolutionOptions] = None,
    ) -> TokenResult:
        opts = options or ResolutionOptions()
        request = TokenRequest(provider_kind=provider_kind, host=host, owner=owner)

        # 0) ENV (highest priority; explicit user intent)
        env_res = self._env.get(request)
        if env_res:
            # Do NOT validate or persist env tokens automatically.
            return env_res

        # 1) GitHub CLI (gh) (auto-read; validate)
        gh_res = self._gh.get(request)
        if gh_res and validate_token(request.provider_kind, request.host, gh_res.token):
            return gh_res

        # 2) Keyring (validate; if invalid -> prompt + overwrite)
        try:
            kr_res = self._keyring.get(request)
            if kr_res:
                if validate_token(request.provider_kind, request.host, kr_res.token):
                    return kr_res

                # Token exists but seems invalid -> re-prompt and overwrite keyring.
                renewed = self._prompt_and_maybe_store(request, opts)
                if renewed:
                    return renewed

        except KeyringUnavailableError as exc:
            # Show a helpful warning once, then continue (prompt fallback).
            self._warn_keyring_unavailable(exc)
        except Exception:
            # Unknown keyring errors: do not block prompting; still avoid hard crash.
            pass

        # 3) Prompt (optional)
        prompt_res = self._prompt_and_maybe_store(request, opts)
        if prompt_res:
            return prompt_res

        raise NoCredentialsError(
            f"No token available for {provider_kind}@{host}"
            + (f" (owner: {owner})" if owner else "")
            + ". Provide it via environment variable, keyring, or gh auth."
        )
