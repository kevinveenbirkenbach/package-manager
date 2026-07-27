from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RepoParts:
    host: str
    port: str | None
    owner: str
    name: str
