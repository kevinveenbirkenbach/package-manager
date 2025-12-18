from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Iterable, Optional, Tuple


@dataclass(frozen=True)
class InstalledVersion:
    """
    Represents a resolved installed version and the matched name.
    """

    name: str
    version: str


def _normalize(name: str) -> str:
    return re.sub(r"[-_.]+", "-", (name or "").strip()).lower()


def _unique_candidates(names: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        if not n:
            continue
        key = _normalize(n)
        if key in seen:
            continue
        seen.add(key)
        out.append(n)
    return out


def get_installed_python_version(*candidates: str) -> Optional[InstalledVersion]:
    """
    Detect installed Python package version in the CURRENT Python environment.

    Strategy:
      1) Exact normalized match using importlib.metadata.version()
      2) Substring fallback by scanning installed distributions
    """
    try:
        from importlib import metadata as importlib_metadata
    except Exception:
        return None

    candidates = _unique_candidates(candidates)

    expanded: list[str] = []
    for c in candidates:
        n = _normalize(c)
        expanded.extend([c, n, n.replace("-", "_"), n.replace("-", ".")])
    expanded = _unique_candidates(expanded)

    # 1) Direct queries first (fast path)
    for name in expanded:
        try:
            version = importlib_metadata.version(name)
            return InstalledVersion(name=name, version=version)
        except Exception:
            continue

    # 2) Fallback: scan distributions (last resort)
    try:
        dists = importlib_metadata.distributions()
    except Exception:
        return None

    norm_candidates = {_normalize(c) for c in candidates}

    for dist in dists:
        dist_name = dist.metadata.get("Name", "") or ""
        norm_dist = _normalize(dist_name)
        for c in norm_candidates:
            if c and (c in norm_dist or norm_dist in c):
                ver = getattr(dist, "version", None)
                if ver:
                    return InstalledVersion(name=dist_name, version=ver)

    return None


def _run_nix(args: list[str]) -> Tuple[int, str, str]:
    p = subprocess.run(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return p.returncode, p.stdout or "", p.stderr or ""


def _extract_version_from_store_path(path: str) -> Optional[str]:
    if not path:
        return None
    base = path.rstrip("/").split("/")[-1]
    if "-" not in base:
        return None
    tail = base.split("-")[-1]
    if re.match(r"\d+(\.\d+){0,3}([a-z0-9+._-]*)?$", tail, re.I):
        return tail
    return None


def get_installed_nix_profile_version(*candidates: str) -> Optional[InstalledVersion]:
    """
    Detect installed version from the current Nix profile.

    Strategy:
      1) JSON output (exact normalized match)
      2) Text fallback (substring)
    """
    if shutil.which("nix") is None:
        return None

    candidates = _unique_candidates(candidates)
    if not candidates:
        return None

    norm_candidates = {_normalize(c) for c in candidates}

    # Preferred: JSON output
    rc, out, _ = _run_nix(["nix", "profile", "list", "--json"])
    if rc == 0 and out.strip():
        try:
            data = json.loads(out)
            elements = data.get("elements") or data.get("items") or {}
            if isinstance(elements, dict):
                for elem in elements.values():
                    if not isinstance(elem, dict):
                        continue
                    name = (elem.get("name") or elem.get("pname") or "").strip()
                    version = (elem.get("version") or "").strip()
                    norm_name = _normalize(name)

                    if norm_name in norm_candidates:
                        if version:
                            return InstalledVersion(name=name, version=version)
                        for sp in elem.get("storePaths", []) or []:
                            guess = _extract_version_from_store_path(sp)
                            if guess:
                                return InstalledVersion(name=name, version=guess)
        except Exception:
            pass

    # Fallback: text mode
    rc, out, _ = _run_nix(["nix", "profile", "list"])
    if rc != 0:
        return None

    for line in out.splitlines():
        norm_line = _normalize(line)
        for c in norm_candidates:
            if c in norm_line:
                m = re.search(r"\b\d+(\.\d+){0,3}[a-z0-9+._-]*\b", line, re.I)
                if m:
                    return InstalledVersion(name=c, version=m.group(0))
                if "/nix/store/" in line:
                    guess = _extract_version_from_store_path(line.split()[-1])
                    if guess:
                        return InstalledVersion(name=c, version=guess)

    return None
