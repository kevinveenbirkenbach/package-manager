from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PyPITarget:
    host: str
    project: str
