# src/pkgmgr/core/credentials/resolver.py
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import Optional

from .providers.env import EnvTokenProvider
from .providers.keyring import KeyringTokenProvider
from .providers.prompt import PromptTokenProvider
from .types import KeyringUnavailableError, NoCredentialsError, TokenRequest, TokenResult


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
        print("       To enable secure token storage, install python-keyring:", file=sys.stderr)
        print("         pip install keyring", file=sys.stderr)
        print("", file=sys.stderr)
        print("       Or install via system packages:", file=sys.stderr)
        print("         sudo apt install python3-keyring", file=sys.stderr)
        print("         sudo pacman -S python-keyring", file=sys.stderr)
        print("         sudo dnf install python3-keyring", file=sys.stderr)
        print("", file=sys.stderr)

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
        except KeyringUnavailableError as exc:
            # Show a helpful warning once, then continue (prompt fallback).
            self._warn_keyring_unavailable(exc)
        except Exception:
            # Unknown keyring errors: do not block prompting; still avoid hard crash.
            pass

        # 3) Prompt (optional)
        if opts.interactive and opts.allow_prompt:
            prompt_res = self._prompt.get(request)
            if prompt_res:
                if opts.save_prompt_token_to_keyring:
                    try:
                        self._keyring.set(request, prompt_res.token)
                    except KeyringUnavailableError as exc:
                        self._warn_keyring_unavailable(exc)
                    except Exception:
                        # If keyring cannot store, still use token for this run.
                        pass
                return prompt_res

        raise NoCredentialsError(
            f"No token available for {provider_kind}@{host}"
            + (f" (owner: {owner})" if owner else "")
            + ". Provide it via environment variable or keyring."
        )
