from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from pkgmgr.actions.branch import tree


class SecretStorageError(Exception):
    pass


def fake_secretstorage(items: list[MagicMock]) -> types.ModuleType:
    module = types.ModuleType("secretstorage")
    module.exceptions = types.SimpleNamespace(SecretStorageException=SecretStorageError)
    module.connection = MagicMock()
    module.dbus_init = MagicMock(return_value=module.connection)
    module.search_items = MagicMock(return_value=iter(items))
    return module


def item(locked: bool, secret: bytes = b"t0ken") -> MagicMock:
    found = MagicMock()
    found.is_locked.return_value = locked
    found.get_secret.return_value = secret
    return found


class TestSecretServiceToken(unittest.TestCase):
    def _token(self, module: types.ModuleType) -> tuple[str | None, str | None]:
        with patch.dict(sys.modules, {"secretstorage": module}):
            return tree.secret_service_token()

    def test_a_locked_item_is_never_unlocked(self) -> None:
        locked = item(True)
        module = fake_secretstorage([locked])
        self.assertEqual(self._token(module), (None, "Secret Service locked"))
        locked.get_secret.assert_not_called()
        locked.unlock.assert_not_called()
        module.connection.close.assert_called_once()

    def test_an_unlocked_item_returns_its_token(self) -> None:
        module = fake_secretstorage([item(True), item(False, b"live")])
        self.assertEqual(self._token(module), ("live", None))
        module.search_items.assert_called_once_with(
            module.connection, {"service": "pkgmgr:github", "username": "github.com|-"}
        )

    def test_no_item_and_no_bus_name_their_reason(self) -> None:
        self.assertEqual(
            self._token(fake_secretstorage([])),
            (None, "no GitHub token in the Secret Service"),
        )
        module = fake_secretstorage([])
        module.dbus_init.side_effect = SecretStorageError("no bus")
        self.assertEqual(
            self._token(module), (None, "Secret Service unavailable: no bus")
        )


if __name__ == "__main__":
    unittest.main()
