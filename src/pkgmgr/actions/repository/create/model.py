from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RepoParts:
    host: str
    port: Optional[str]
    owner: str
    name: str
