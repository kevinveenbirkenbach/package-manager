# tests/unit/pkgmgr/test_capabilities.py

import unittest
from unittest.mock import patch, mock_open

from pkgmgr.actions.install.capabilities import (
    PythonRuntimeCapability,
    MakeInstallCapability,
    NixFlakeCapability,
    CapabilityMatcher,
    detect_capabilities,
    resolve_effective_capabilities,
    LAYER_ORDER,
)


class DummyCtx:
    """Minimal RepoContext stub with just repo_dir."""

    def __init__(self, repo_dir: str):
        self.repo_dir = repo_dir


# ---------------------------------------------------------------------------
# Tests for individual capability detectors
# ---------------------------------------------------------------------------


class TestCapabilitiesDetectors(unittest.TestCase):
    def setUp(self):
        self.ctx = DummyCtx("/tmp/repo")

    @patch("pkgmgr.actions.install.capabilities.os.path.exists")
    def test_python_runtime_python_layer_pyproject(self, mock_exists):
        """PythonRuntimeCapability: python layer is provided if pyproject.toml exists."""
        cap = PythonRuntimeCapability()

        def exists_side_effect(path):
            return path.endswith("pyproject.toml")

        mock_exists.side_effect = exists_side_effect

        self.assertTrue(cap.applies_to_layer("python"))
        self.assertTrue(cap.is_provided(self.ctx, "python"))
        # Other layers should not be treated as python-runtime by this branch
        self.assertFalse(cap.is_provided(self.ctx, "nix"))
        self.assertFalse(cap.is_provided(self.ctx, "os-packages"))

    @patch("pkgmgr.actions.install.capabilities._read_text_if_exists")
    @patch("pkgmgr.actions.install.capabilities.os.path.exists")
    def test_python_runtime_nix_layer_flake(self, mock_exists, mock_read):
        """
        PythonRuntimeCapability: nix layer is provided if flake.nix contains
        Python-related patterns like buildPythonApplication.
        """
        cap = PythonRuntimeCapability()

        def exists_side_effect(path):
            return path.endswith("flake.nix")

        mock_exists.side_effect = exists_side_effect
        mock_read.return_value = "buildPythonApplication something"

        self.assertTrue(cap.applies_to_layer("nix"))
        self.assertTrue(cap.is_provided(self.ctx, "nix"))

    @patch("pkgmgr.actions.install.capabilities.os.path.exists", return_value=True)
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="install:\n\t echo 'installing'\n",
    )
    def test_make_install_makefile_layer(self, mock_file, mock_exists):
        """MakeInstallCapability: makefile layer is provided if Makefile has an install target."""
        cap = MakeInstallCapability()

        self.assertTrue(cap.applies_to_layer("makefile"))
        self.assertTrue(cap.is_provided(self.ctx, "makefile"))

    @patch("pkgmgr.actions.install.capabilities.os.path.exists")
    def test_nix_flake_capability_on_nix_layer(self, mock_exists):
        """NixFlakeCapability: nix layer is provided if flake.nix exists."""
        cap = NixFlakeCapability()

        def exists_side_effect(path):
            return path.endswith("flake.nix")

        mock_exists.side_effect = exists_side_effect

        self.assertTrue(cap.applies_to_layer("nix"))
        self.assertTrue(cap.is_provided(self.ctx, "nix"))


# ---------------------------------------------------------------------------
# Dummy capability matcher for resolver tests
# ---------------------------------------------------------------------------


class DummyCapability(CapabilityMatcher):
    """
    Simple test capability that returns True/False based on a static mapping:

        mapping = {
            "makefile": True,
            "python":   False,
            "nix":      True,
            ...
        }
    """

    def __init__(self, name: str, mapping: dict[str, bool]):
        self.name = name
        self._mapping = mapping

    def applies_to_layer(self, layer: str) -> bool:
        return layer in self._mapping

    def is_provided(self, ctx: DummyCtx, layer: str) -> bool:
        # ctx is unused here; we are testing the resolution logic, not IO
        return self._mapping.get(layer, False)


# ---------------------------------------------------------------------------
# Tests for detect_capabilities (raw detection)
# ---------------------------------------------------------------------------


class TestDetectCapabilities(unittest.TestCase):
    def setUp(self):
        self.ctx = DummyCtx("/tmp/repo")

    def test_detect_capabilities_with_dummy_matchers(self):
        """
        detect_capabilities should aggregate all capabilities per layer
        based on the matchers' applies_to_layer/is_provided logic.
        """
        layers = ["makefile", "python", "nix", "os-packages"]

        dummy1 = DummyCapability(
            "cap-a",
            {
                "makefile": True,
                "python": False,
                "nix": True,
            },
        )
        dummy2 = DummyCapability(
            "cap-b",
            {
                "python": True,
                "os-packages": True,
            },
        )

        with patch(
            "pkgmgr.actions.install.capabilities.CAPABILITY_MATCHERS", [dummy1, dummy2]
        ):
            caps = detect_capabilities(self.ctx, layers)

        self.assertEqual(
            caps,
            {
                "makefile": {"cap-a"},
                "python": {"cap-b"},
                "nix": {"cap-a"},
                "os-packages": {"cap-b"},
            },
        )


# ---------------------------------------------------------------------------
# Tests for resolve_effective_capabilities (bottom-up shadowing)
# ---------------------------------------------------------------------------


class TestResolveEffectiveCapabilities(unittest.TestCase):
    def setUp(self):
        self.ctx = DummyCtx("/tmp/repo")

    def test_bottom_up_shadowing_makefile_python_nix(self):
        """
        Scenario:
          - makefile: provides make-install
          - python:   provides python-runtime, make-install
          - nix:      provides python-runtime, make-install, nix-flake
          - os-packages: none

        Expected effective capabilities:
          - makefile:    {}
          - python:      {}
          - nix:         {python-runtime, make-install, nix-flake}
          - os-packages: {}
        """
        layers = ["makefile", "python", "nix", "os-packages"]

        cap_make_install = DummyCapability(
            "make-install",
            {
                "makefile": True,
                "python": True,
                "nix": True,
                "os-packages": False,
            },
        )
        cap_python_runtime = DummyCapability(
            "python-runtime",
            {
                "makefile": False,
                "python": True,
                "nix": True,
                "os-packages": False,
            },
        )
        cap_nix_flake = DummyCapability(
            "nix-flake",
            {
                "makefile": False,
                "python": False,
                "nix": True,
                "os-packages": False,
            },
        )

        with patch(
            "pkgmgr.actions.install.capabilities.CAPABILITY_MATCHERS",
            [cap_make_install, cap_python_runtime, cap_nix_flake],
        ):
            effective = resolve_effective_capabilities(self.ctx, layers)

        self.assertEqual(effective["makefile"], set())
        self.assertEqual(effective["python"], set())
        self.assertEqual(
            effective["nix"],
            {"python-runtime", "make-install", "nix-flake"},
        )
        self.assertEqual(effective["os-packages"], set())

    def test_os_packages_shadow_all_lower_layers(self):
        """
        Scenario:
          - python:      provides python-runtime
          - nix:         provides python-runtime
          - os-packages: provides python-runtime

        Expected effective capabilities:
          - python:      {}
          - nix:         {}
          - os-packages: {python-runtime}
        """
        layers = ["python", "nix", "os-packages"]

        cap_python_runtime = DummyCapability(
            "python-runtime",
            {
                "python": True,
                "nix": True,
                "os-packages": True,
            },
        )

        with patch(
            "pkgmgr.actions.install.capabilities.CAPABILITY_MATCHERS",
            [cap_python_runtime],
        ):
            effective = resolve_effective_capabilities(self.ctx, layers)

        self.assertEqual(effective["python"], set())
        self.assertEqual(effective["nix"], set())
        self.assertEqual(effective["os-packages"], {"python-runtime"})

    def test_capability_only_in_lowest_layer(self):
        """
        If a capability is only provided by the lowest layer, it should remain
        attached to that layer as an effective capability.
        """
        layers = ["makefile", "python", "nix"]

        cap_only_make = DummyCapability(
            "make-install",
            {
                "makefile": True,
                "python": False,
                "nix": False,
            },
        )

        with patch(
            "pkgmgr.actions.install.capabilities.CAPABILITY_MATCHERS", [cap_only_make]
        ):
            effective = resolve_effective_capabilities(self.ctx, layers)

        self.assertEqual(effective["makefile"], {"make-install"})
        self.assertEqual(effective["python"], set())
        self.assertEqual(effective["nix"], set())

    def test_capability_only_in_highest_layer(self):
        """
        If a capability is only provided by the highest layer, it should appear
        only there as an effective capability.
        """
        layers = ["makefile", "python", "nix"]

        cap_only_nix = DummyCapability(
            "nix-flake",
            {
                "makefile": False,
                "python": False,
                "nix": True,
            },
        )

        with patch(
            "pkgmgr.actions.install.capabilities.CAPABILITY_MATCHERS", [cap_only_nix]
        ):
            effective = resolve_effective_capabilities(self.ctx, layers)

        self.assertEqual(effective["makefile"], set())
        self.assertEqual(effective["python"], set())
        self.assertEqual(effective["nix"], {"nix-flake"})

    def test_partial_layer_subset_order_respected(self):
        """
        When passing a custom subset of layers, the resolver must respect
        that custom order for shadowing.

        Scenario:
          - layers = ["python", "nix"]
          - both provide "python-runtime"

        Expected:
          - python: {}
          - nix:    {"python-runtime"}
        """
        layers = ["python", "nix"]

        cap_python_runtime = DummyCapability(
            "python-runtime",
            {
                "python": True,
                "nix": True,
            },
        )

        with patch(
            "pkgmgr.actions.install.capabilities.CAPABILITY_MATCHERS",
            [cap_python_runtime],
        ):
            effective = resolve_effective_capabilities(self.ctx, layers)

        self.assertEqual(effective["python"], set())
        self.assertEqual(effective["nix"], {"python-runtime"})

    def test_default_layer_order_is_used_if_none_given(self):
        """
        If no explicit layers are passed, resolve_effective_capabilities
        should use LAYER_ORDER.
        """
        cap_dummy = DummyCapability(
            "dummy-cap",
            {
                # Only provide something on the highest default layer
                LAYER_ORDER[-1]: True,
            },
        )

        with patch(
            "pkgmgr.actions.install.capabilities.CAPABILITY_MATCHERS",
            [cap_dummy],
        ):
            effective = resolve_effective_capabilities(self.ctx)

        # All lower layers must be empty; highest default layer must have the cap
        for layer in LAYER_ORDER[:-1]:
            self.assertEqual(effective[layer], set())
        self.assertEqual(effective[LAYER_ORDER[-1]], {"dummy-cap"})


if __name__ == "__main__":
    unittest.main()
