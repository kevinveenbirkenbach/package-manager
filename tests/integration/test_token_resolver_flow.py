from __future__ import annotations

import unittest
from unittest.mock import patch

from pkgmgr.core.credentials.resolver import TokenResolver
from pkgmgr.core.credentials.types import TokenResult


class TestTokenResolverIntegration(unittest.TestCase):
    def test_full_resolution_flow_with_invalid_gh_and_keyring_then_prompt(self) -> None:
        """
        Full integration scenario:

        - ENV provides nothing
        - GitHub CLI (gh) is available and returns a token, but it is INVALID
        - Keyring contains a token, but it is INVALID
        - Interactive prompt provides a NEW token
        - New token is ACCEPTED and OVERWRITES the keyring entry
        """

        resolver = TokenResolver()

        # ------------------------------------------------------------------
        # 1) ENV: empty
        # ------------------------------------------------------------------
        with patch.dict("os.environ", {}, clear=True):
            # ------------------------------------------------------------------
            # 2) GH CLI is available
            # ------------------------------------------------------------------
            with patch(
                "pkgmgr.core.credentials.providers.gh.shutil.which",
                return_value="/usr/bin/gh",
            ):
                with patch(
                    "pkgmgr.core.credentials.providers.gh.subprocess.check_output",
                    return_value="gh-invalid-token\n",
                ):
                    # ------------------------------------------------------------------
                    # 3) Keyring returns an existing (invalid) token
                    # ------------------------------------------------------------------
                    with patch(
                        "pkgmgr.core.credentials.providers.keyring._import_keyring"
                    ) as mock_import_keyring:
                        mock_keyring = mock_import_keyring.return_value
                        mock_keyring.get_password.return_value = "keyring-invalid-token"

                        # ------------------------------------------------------------------
                        # 4) Prompt is allowed and returns a NEW token
                        # ------------------------------------------------------------------
                        with patch(
                            "pkgmgr.core.credentials.providers.prompt.sys.stdin.isatty",
                            return_value=True,
                        ):
                            with patch(
                                "pkgmgr.core.credentials.providers.prompt.getpass",
                                return_value="new-valid-token",
                            ):
                                # ------------------------------------------------------------------
                                # 5) Validation logic:
                                #    - gh token invalid
                                #    - keyring token invalid
                                #    - prompt token is NOT validated (by design)
                                # ------------------------------------------------------------------
                                def validate_side_effect(
                                    provider_kind: str,
                                    host: str,
                                    token: str,
                                ) -> bool:
                                    return False  # gh + keyring invalid

                                with patch(
                                    "pkgmgr.core.credentials.resolver.validate_token",
                                    side_effect=validate_side_effect,
                                ) as validate_mock:
                                    result = resolver.get_token(
                                        provider_kind="github",
                                        host="github.com",
                                    )

        # ----------------------------------------------------------------------
        # Assertions
        # ----------------------------------------------------------------------
        self.assertIsInstance(result, TokenResult)
        self.assertEqual(result.token, "new-valid-token")
        self.assertEqual(result.source, "prompt")

        # validate_token was called ONLY for gh and keyring
        validated_tokens = [call.args[2] for call in validate_mock.call_args_list]
        self.assertIn("gh-invalid-token", validated_tokens)
        self.assertIn("keyring-invalid-token", validated_tokens)
        self.assertNotIn("new-valid-token", validated_tokens)

        # Keyring must be overwritten with the new token
        mock_keyring.set_password.assert_called_once()
        service, username, stored_token = mock_keyring.set_password.call_args.args
        self.assertEqual(stored_token, "new-valid-token")


if __name__ == "__main__":
    unittest.main()
