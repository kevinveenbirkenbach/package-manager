# src/pkgmgr/core/remote_provisioning/http/client.py
from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .errors import HttpError


@dataclass(frozen=True)
class HttpResponse:
    status: int
    text: str
    json: Optional[Dict[str, Any]] = None


class HttpClient:
    """Tiny HTTP client (stdlib) with JSON support."""

    def __init__(self, timeout_s: int = 15) -> None:
        self._timeout_s = int(timeout_s)

    def request_json(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> HttpResponse:
        data: Optional[bytes] = None
        final_headers: Dict[str, str] = dict(headers or {})

        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            final_headers.setdefault("Content-Type", "application/json")

        req = urllib.request.Request(url=url, data=data, method=method.upper())
        for k, v in final_headers.items():
            req.add_header(k, v)

        try:
            with urllib.request.urlopen(
                req,
                timeout=self._timeout_s,
                context=ssl.create_default_context(),
            ) as resp:
                raw = resp.read().decode("utf-8", errors="replace")

                parsed: Optional[Dict[str, Any]] = None
                if raw:
                    try:
                        loaded = json.loads(raw)
                        parsed = loaded if isinstance(loaded, dict) else None
                    except Exception:
                        parsed = None

                return HttpResponse(status=int(resp.status), text=raw, json=parsed)
        except urllib.error.HTTPError as exc:
            try:
                body = exc.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            raise HttpError(status=int(exc.code), message=str(exc), body=body) from exc
        except urllib.error.URLError as exc:
            raise HttpError(status=0, message=str(exc), body="") from exc
