#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict


def read_os_release(path: str = "/etc/os-release") -> Dict[str, str]:
    """
    Parse /etc/os-release into a dict. Returns empty dict if missing.
    """
    if not os.path.exists(path):
        return {}

    result: Dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip().strip('"')
    return result


@dataclass(frozen=True)
class OSReleaseInfo:
    """
    Minimal /etc/os-release representation for distro detection.
    """

    id: str = ""
    id_like: str = ""
    pretty_name: str = ""

    @staticmethod
    def load() -> "OSReleaseInfo":
        data = read_os_release()
        return OSReleaseInfo(
            id=(data.get("ID") or "").lower(),
            id_like=(data.get("ID_LIKE") or "").lower(),
            pretty_name=(data.get("PRETTY_NAME") or ""),
        )

    def ids(self) -> set[str]:
        ids: set[str] = set()
        if self.id:
            ids.add(self.id)
        if self.id_like:
            for part in self.id_like.split():
                ids.add(part.strip())
        return ids

    def is_arch_family(self) -> bool:
        ids = self.ids()
        return ("arch" in ids) or ("archlinux" in ids)

    def is_debian_family(self) -> bool:
        ids = self.ids()
        return bool(ids.intersection({"debian", "ubuntu"}))

    def is_fedora_family(self) -> bool:
        ids = self.ids()
        return bool(
            ids.intersection({"fedora", "rhel", "centos", "rocky", "almalinux"})
        )
