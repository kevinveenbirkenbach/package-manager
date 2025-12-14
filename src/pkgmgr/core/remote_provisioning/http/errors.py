# src/pkgmgr/core/remote_provisioning/http/errors.py
from __future__ import annotations


class HttpError(RuntimeError):
    def __init__(self, status: int, message: str, body: str = "") -> None:
        super().__init__(message)
        self.status = status
        self.body = body
