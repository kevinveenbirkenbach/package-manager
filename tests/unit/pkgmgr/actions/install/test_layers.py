#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import unittest

from pkgmgr.actions.repository.install.layers import (
    CliLayer,
    CLI_LAYERS,
    classify_command_layer,
    layer_priority,
)


class TestCliLayerAndPriority(unittest.TestCase):
    def test_layer_priority_for_known_layers_is_monotonic(self) -> None:
        """
        layer_priority() must reflect the ordering in CLI_LAYERS.
        We mainly check that the order is stable and that each later item
        has a higher (or equal) priority index than the previous one.
        """
        priorities = [layer_priority(layer) for layer in CLI_LAYERS]

        # Ensure no negative priorities and strictly increasing or stable order
        for idx, value in enumerate(priorities):
            self.assertGreaterEqual(
                value, 0, f"Priority for {CLI_LAYERS[idx]} must be >= 0"
            )
            if idx > 0:
                self.assertGreaterEqual(
                    value,
                    priorities[idx - 1],
                    "Priorities must be non-decreasing in CLI_LAYERS order",
                )

    def test_layer_priority_for_none_and_unknown(self) -> None:
        """
        None and unknown layers should both receive the 'max' priority
        (i.e., len(CLI_LAYERS)).
        """
        none_priority = layer_priority(None)
        self.assertEqual(none_priority, len(CLI_LAYERS))

        class FakeLayer:
            # Not part of CliLayer
            pass

        unknown_priority = layer_priority(FakeLayer())  # type: ignore[arg-type]
        self.assertEqual(unknown_priority, len(CLI_LAYERS))


class TestClassifyCommandLayer(unittest.TestCase):
    def setUp(self) -> None:
        self.home = os.path.expanduser("~")
        self.repo_dir = "/tmp/pkgmgr-test-repo"

    def test_classify_system_binaries_os_packages(self) -> None:
        for cmd in ("/usr/bin/pkgmgr", "/bin/pkgmgr"):
            with self.subTest(cmd=cmd):
                layer = classify_command_layer(cmd, self.repo_dir)
                self.assertEqual(layer, CliLayer.OS_PACKAGES)

    def test_classify_nix_binaries(self) -> None:
        nix_cmds = [
            "/nix/store/abcd1234-bin-pkgmgr/bin/pkgmgr",
            os.path.join(self.home, ".nix-profile", "bin", "pkgmgr"),
        ]
        for cmd in nix_cmds:
            with self.subTest(cmd=cmd):
                layer = classify_command_layer(cmd, self.repo_dir)
                self.assertEqual(layer, CliLayer.NIX)

    def test_classify_python_binaries(self) -> None:
        # Default Python/virtualenv-style location in home
        cmd = os.path.join(self.home, ".local", "bin", "pkgmgr")
        layer = classify_command_layer(cmd, self.repo_dir)
        self.assertEqual(layer, CliLayer.PYTHON)

    def test_classify_repo_local_binary_makefile_layer(self) -> None:
        cmd = os.path.join(self.repo_dir, "bin", "pkgmgr")
        layer = classify_command_layer(cmd, self.repo_dir)
        self.assertEqual(layer, CliLayer.MAKEFILE)

    def test_fallback_to_python_layer(self) -> None:
        """
        Non-system, non-nix, non-repo binaries should fall back to PYTHON.
        """
        cmd = "/opt/pkgmgr/bin/pkgmgr"
        layer = classify_command_layer(cmd, self.repo_dir)
        self.assertEqual(layer, CliLayer.PYTHON)


if __name__ == "__main__":
    unittest.main()
