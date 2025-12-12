#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Capability detection for pkgmgr.

Each capability is represented by a class that:
  - defines a logical name (e.g. "python-runtime", "make-install", "nix-flake")
  - knows for which installer layer(s) it applies (e.g. "nix", "python",
    "makefile", "os-packages")
  - searches the repository config/build files for specific strings
    to determine whether that capability is provided by that layer.

This allows pkgmgr to dynamically decide if a higher layer already covers
work a lower layer would otherwise do (e.g. Nix calling pyproject/make,
or distro packages wrapping Nix or Makefile logic).

On top of the raw detection, this module also exposes a bottom-up
"effective capability" resolver:

  - We start from the lowest layer (e.g. "makefile") and go upwards.
  - For each capability provided by a lower layer, we check whether any
    higher layer also provides the same capability.
  - If yes, we consider the capability "shadowed" by the higher layer;
    the lower layer does not list it as an effective capability.
  - If no higher layer provides it, the capability remains attached to
    the lower layer.

This yields, for each layer, only those capabilities that are not
redundant with respect to higher layers in the stack.
"""

from __future__ import annotations

import glob
import os
from abc import ABC, abstractmethod
from typing import Iterable, TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from pkgmgr.actions.install.context import RepoContext


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _read_text_if_exists(path: str) -> Optional[str]:
    """Read a file as UTF-8 text, returning None if it does not exist or fails."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def _scan_files_for_patterns(files: Iterable[str], patterns: Iterable[str]) -> bool:
    """
    Return True if any of the given files exists and contains at least one of
    the given patterns (case-insensitive).
    """
    lower_patterns = [p.lower() for p in patterns]
    for path in files:
        if not path:
            continue
        content = _read_text_if_exists(path)
        if not content:
            continue
        lower_content = content.lower()
        if any(p in lower_content for p in lower_patterns):
            return True
    return False


def _first_spec_file(repo_dir: str) -> Optional[str]:
    """Return the first *.spec file in repo_dir, if any."""
    matches = glob.glob(os.path.join(repo_dir, "*.spec"))
    if not matches:
        return None
    return sorted(matches)[0]


# ---------------------------------------------------------------------------
# Base matcher
# ---------------------------------------------------------------------------


class CapabilityMatcher(ABC):
    """Base class for all capability detectors."""

    #: Logical capability name (e.g. "python-runtime", "make-install").
    name: str

    @abstractmethod
    def applies_to_layer(self, layer: str) -> bool:
        """Return True if this capability can be provided by the given layer."""
        raise NotImplementedError

    @abstractmethod
    def is_provided(self, ctx: "RepoContext", layer: str) -> bool:
        """
        Return True if this capability is actually provided by the given layer
        for this repository.

        This is where we search for specific strings in build/config files
        (flake.nix, pyproject.toml, Makefile, PKGBUILD, debian/rules, *.spec, ...).
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Capability: python-runtime
#
# Provided when:
#   - Layer "python":
#       pyproject.toml exists → Python runtime via pip for this project
#   - Layer "nix":
#       flake.nix contains hints that it builds a Python app
#       (buildPythonApplication, python3Packages., poetry2nix, pip install, ...)
#   - Layer "os-packages":
#       distro build scripts (PKGBUILD, debian/rules, *.spec) clearly call
#       pip/python to install THIS Python project (heuristic).
# ---------------------------------------------------------------------------


class PythonRuntimeCapability(CapabilityMatcher):
    name = "python-runtime"

    def applies_to_layer(self, layer: str) -> bool:
        # OS packages may wrap Python builds, but must explicitly prove it
        return layer in {"python", "nix", "os-packages"}

    def is_provided(self, ctx: "RepoContext", layer: str) -> bool:
        repo_dir = ctx.repo_dir

        if layer == "python":
            # For pkgmgr, a pyproject.toml is enough to say:
            # "This layer provides the Python runtime for this project."
            pyproject = os.path.join(repo_dir, "pyproject.toml")
            return os.path.exists(pyproject)

        if layer == "nix":
            flake = os.path.join(repo_dir, "flake.nix")
            content = _read_text_if_exists(flake)
            if not content:
                return False

            content = content.lower()
            patterns = [
                "buildpythonapplication",
                "python3packages.",
                "poetry2nix",
                "pip install",
                "python -m pip",
            ]
            return any(p in content for p in patterns)

        if layer == "os-packages":
            # Heuristic:
            #   - repo looks like a Python project (pyproject.toml or setup.py)
            #   - and OS build scripts call pip / python -m pip / setup.py install
            pyproject = os.path.join(repo_dir, "pyproject.toml")
            setup_py = os.path.join(repo_dir, "setup.py")
            if not (os.path.exists(pyproject) or os.path.exists(setup_py)):
                return False

            pkgbuild = os.path.join(repo_dir, "PKGBUILD")
            debian_rules = os.path.join(repo_dir, "debian", "rules")
            spec = _first_spec_file(repo_dir)

            scripts = [pkgbuild, debian_rules]
            if spec:
                scripts.append(spec)

            patterns = [
                "pip install .",
                "python -m pip install",
                "python3 -m pip install",
                "setup.py install",
            ]
            return _scan_files_for_patterns(scripts, patterns)

        return False


# ---------------------------------------------------------------------------
# Capability: make-install
#
# Provided when:
#   - Layer "makefile":
#       Makefile has an "install:" target
#   - Layer "python":
#       pyproject.toml mentions "make install"
#   - Layer "nix":
#       flake.nix mentions "make install"
#   - Layer "os-packages":
#       distro build scripts call "make install" (they already consume the
#       Makefile installation step).
# ---------------------------------------------------------------------------


class MakeInstallCapability(CapabilityMatcher):
    name = "make-install"

    def applies_to_layer(self, layer: str) -> bool:
        return layer in {"makefile", "python", "nix", "os-packages"}

    def is_provided(self, ctx: "RepoContext", layer: str) -> bool:
        repo_dir = ctx.repo_dir

        if layer == "makefile":
            makefile = os.path.join(repo_dir, "Makefile")
            if not os.path.exists(makefile):
                return False
            try:
                with open(makefile, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip().startswith("install:"):
                            return True
            except OSError:
                return False
            return False

        if layer == "python":
            pyproject = os.path.join(repo_dir, "pyproject.toml")
            content = _read_text_if_exists(pyproject)
            if not content:
                return False
            return "make install" in content.lower()

        if layer == "nix":
            flake = os.path.join(repo_dir, "flake.nix")
            content = _read_text_if_exists(flake)
            if not content:
                return False
            return "make install" in content.lower()

        if layer == "os-packages":
            pkgbuild = os.path.join(repo_dir, "PKGBUILD")
            debian_rules = os.path.join(repo_dir, "debian", "rules")
            spec = _first_spec_file(repo_dir)

            scripts = [pkgbuild, debian_rules]
            if spec:
                scripts.append(spec)

            # If any OS build script calls "make install", we assume it is
            # already consuming the Makefile installation and thus provides
            # the make-install capability.
            return _scan_files_for_patterns(scripts, ["make install"])

        return False


# ---------------------------------------------------------------------------
# Capability: nix-flake
#
# Provided when:
#   - Layer "nix":
#       flake.nix exists → Nix flake installer can install this project
#   - Layer "os-packages":
#       distro build scripts clearly call Nix (nix build/run/develop/profile),
#       i.e. they already use Nix as part of building/installing.
# ---------------------------------------------------------------------------


class NixFlakeCapability(CapabilityMatcher):
    name = "nix-flake"

    def applies_to_layer(self, layer: str) -> bool:
        # Only Nix itself and OS packages that explicitly wrap Nix
        return layer in {"nix", "os-packages"}

    def is_provided(self, ctx: "RepoContext", layer: str) -> bool:
        repo_dir = ctx.repo_dir

        if layer == "nix":
            flake = os.path.join(repo_dir, "flake.nix")
            return os.path.exists(flake)

        if layer == "os-packages":
            pkgbuild = os.path.join(repo_dir, "PKGBUILD")
            debian_rules = os.path.join(repo_dir, "debian", "rules")
            spec = _first_spec_file(repo_dir)

            scripts = [pkgbuild, debian_rules]
            if spec:
                scripts.append(spec)

            patterns = [
                "nix build",
                "nix run",
                "nix-shell",
                "nix develop",
                "nix profile",
            ]
            return _scan_files_for_patterns(scripts, patterns)

        return False


# ---------------------------------------------------------------------------
# Registry of all capability matchers currently supported.
# ---------------------------------------------------------------------------

CAPABILITY_MATCHERS: list[CapabilityMatcher] = [
    PythonRuntimeCapability(),
    MakeInstallCapability(),
    NixFlakeCapability(),
]


# ---------------------------------------------------------------------------
# Layer ordering and effective capability resolution
# ---------------------------------------------------------------------------

#: Default bottom-up order of installer layers.
#: Lower indices = lower layers; higher indices = higher layers.
LAYER_ORDER: list[str] = [
    "makefile",
    "python",
    "nix",
    "os-packages",
]


def detect_capabilities(
    ctx: "RepoContext",
    layers: Iterable[str],
) -> dict[str, set[str]]:
    """
    Perform raw capability detection per layer, without any shadowing.

    Returns a mapping:

        {
            "makefile":    {"make-install"},
            "python":      {"python-runtime", "make-install"},
            "nix":         {"python-runtime", "make-install", "nix-flake"},
            "os-packages": set(),
        }

    depending on which matchers report capabilities for each layer.
    """
    layers_list = list(layers)
    caps_by_layer: dict[str, set[str]] = {layer: set() for layer in layers_list}

    for matcher in CAPABILITY_MATCHERS:
        for layer in layers_list:
            if not matcher.applies_to_layer(layer):
                continue
            if matcher.is_provided(ctx, layer):
                caps_by_layer[layer].add(matcher.name)

    return caps_by_layer


def resolve_effective_capabilities(
    ctx: "RepoContext",
    layers: Optional[Iterable[str]] = None,
) -> dict[str, set[str]]:
    """
    Resolve *effective* capabilities for each layer using a bottom-up strategy.

    Algorithm (layer-agnostic, works for all layers in the given order):

      1. Run raw detection (detect_capabilities) to obtain which capabilities
         are provided by which layer.
      2. Iterate layers from bottom to top (the order in `layers`):
           For each capability that a lower layer provides, check whether
           any *higher* layer also provides the same capability.
           - If yes, the capability is considered "shadowed" by the higher
             layer and is NOT listed as effective for the lower layer.
           - If no higher layer provides it, it remains as an effective
             capability of the lower layer.
      3. Return a mapping layer → set of effective capabilities.

    This means *any* higher layer can overshadow a lower layer, not just
    a specific one like Nix. The resolver is completely generic.
    """
    if layers is None:
        layers_list = list(LAYER_ORDER)
    else:
        layers_list = list(layers)

    raw_caps = detect_capabilities(ctx, layers_list)
    effective: dict[str, set[str]] = {layer: set() for layer in layers_list}

    # Bottom-up walk: lower index = lower layer, higher index = higher layer
    for idx, lower in enumerate(layers_list):
        lower_caps = raw_caps.get(lower, set())
        for cap in lower_caps:
            # Check if any higher layer also provides this capability
            covered_by_higher = False
            for higher in layers_list[idx + 1 :]:
                higher_caps = raw_caps.get(higher, set())
                if cap in higher_caps:
                    covered_by_higher = True
                    break

            if not covered_by_higher:
                effective[lower].add(cap)

    return effective
