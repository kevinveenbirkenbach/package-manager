"""Error-path tests: pkgmgr must degrade, not crash, on broken input.

pkgmgr probes external toolchains and parses packaging metadata it does
not control. Every test here injects one concrete failure -- undecodable
bytes, malformed YAML, a missing binary, an unreachable host -- and
asserts the documented fallback: return None, warn and continue, or skip
the entry.

Faults are injected for real wherever possible rather than mocked, so the
exception types listed in the handlers are the ones actually raised.
"""

from __future__ import annotations

import importlib.util
import io
import os
import subprocess
import tempfile
import unittest
import urllib.error
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

BAD_UTF8 = b"\xff\xfe\x00\x80version = 1"

# tomli is only a dependency below Python 3.11, so the fallback branch is
# only exercisable where it is actually installed.
HAS_TOMLI = importlib.util.find_spec("tomli") is not None


def _write(path: str, data: bytes | str) -> str:
    mode = "wb" if isinstance(data, bytes) else "w"
    with open(path, mode) as handle:
        handle.write(data)
    return path


class TestVersionSourceDegradation(unittest.TestCase):
    """src/pkgmgr/core/version/source.py"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = self.tmp.name

    def test_broken_toml_returns_none(self) -> None:
        from pkgmgr.core.version.source import (
            read_pyproject_project_name,
            read_pyproject_version,
        )

        _write(os.path.join(self.dir, "pyproject.toml"), "this is [[[ not toml")
        self.assertIsNone(read_pyproject_version(self.dir))
        self.assertIsNone(read_pyproject_project_name(self.dir))

    def test_undecodable_toml_returns_none(self) -> None:
        from pkgmgr.core.version.source import read_pyproject_version

        _write(os.path.join(self.dir, "pyproject.toml"), BAD_UTF8)
        self.assertIsNone(read_pyproject_version(self.dir))

    def test_unreadable_pyproject_returns_none(self) -> None:
        from pkgmgr.core.version.source import read_pyproject_version

        _write(os.path.join(self.dir, "pyproject.toml"), '[project]\nversion = "1.0.0"\n')
        with patch("builtins.open", side_effect=OSError("EIO")):
            self.assertIsNone(read_pyproject_version(self.dir))

    def test_undecodable_flake_returns_none(self) -> None:
        from pkgmgr.core.version.source import read_flake_version

        _write(os.path.join(self.dir, "flake.nix"), BAD_UTF8)
        self.assertIsNone(read_flake_version(self.dir))

    def test_undecodable_pkgbuild_returns_none(self) -> None:
        from pkgmgr.core.version.source import read_pkgbuild_version

        _write(os.path.join(self.dir, "PKGBUILD"), BAD_UTF8)
        self.assertIsNone(read_pkgbuild_version(self.dir))

    def test_undecodable_debian_changelog_returns_none(self) -> None:
        from pkgmgr.core.version.source import read_debian_changelog_version

        os.makedirs(os.path.join(self.dir, "debian"), exist_ok=True)
        _write(os.path.join(self.dir, "debian", "changelog"), BAD_UTF8)
        self.assertIsNone(read_debian_changelog_version(self.dir))

    def test_undecodable_spec_returns_none(self) -> None:
        from pkgmgr.core.version.source import read_spec_version

        _write(os.path.join(self.dir, "pkg.spec"), BAD_UTF8)
        self.assertIsNone(read_spec_version(self.dir))

    def test_broken_galaxy_yaml_returns_none(self) -> None:
        from pkgmgr.core.version.source import read_ansible_galaxy_version

        _write(os.path.join(self.dir, "galaxy.yml"), "::: not: valid: yaml:::\n  - [")
        self.assertIsNone(read_ansible_galaxy_version(self.dir))

    def test_broken_meta_main_yaml_returns_none(self) -> None:
        from pkgmgr.core.version.source import read_ansible_galaxy_version

        os.makedirs(os.path.join(self.dir, "meta"), exist_ok=True)
        _write(os.path.join(self.dir, "meta", "main.yml"), "a: [1,\nb: }{")
        self.assertIsNone(read_ansible_galaxy_version(self.dir))

    @unittest.skipUnless(HAS_TOMLI, "tomli is not installed")
    def test_missing_tomllib_falls_back_to_tomli(self) -> None:
        import builtins

        from pkgmgr.core.version.source import read_pyproject_version

        _write(os.path.join(self.dir, "pyproject.toml"), '[project]\nversion = "9.9.9"\n')
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "tomllib":
                raise ImportError("no tomllib on this interpreter")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            self.assertEqual(read_pyproject_version(self.dir), "9.9.9")


class TestInstalledVersionDegradation(unittest.TestCase):
    """src/pkgmgr/core/version/installed.py"""

    def test_unknown_distribution_returns_none(self) -> None:
        from pkgmgr.core.version.installed import get_installed_python_version

        self.assertIsNone(get_installed_python_version("no-such-distribution-xyz"))

    def test_missing_importlib_metadata_returns_none(self) -> None:
        import builtins

        from pkgmgr.core.version.installed import get_installed_python_version

        real_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "importlib" and fromlist and "metadata" in fromlist:
                raise ImportError("no importlib.metadata")
            return real_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", side_effect=fake_import):
            self.assertIsNone(get_installed_python_version("kpmx"))

    def test_broken_distribution_scan_returns_none(self) -> None:
        from importlib import metadata as importlib_metadata

        from pkgmgr.core.version.installed import get_installed_python_version

        with (
            patch.object(
                importlib_metadata,
                "version",
                side_effect=importlib_metadata.PackageNotFoundError("nope"),
            ),
            patch.object(
                importlib_metadata, "distributions", side_effect=OSError("broken env")
            ),
        ):
            self.assertIsNone(get_installed_python_version("kpmx"))

    def test_non_json_nix_profile_output_falls_back_to_text_mode(self) -> None:
        import pkgmgr.core.version.installed as mod

        with (
            patch.object(mod.shutil, "which", return_value="/usr/bin/nix"),
            patch.object(mod, "_run_nix", return_value=(0, "not json at all", "")),
        ):
            self.assertIsNone(mod.get_installed_nix_profile_version("pkgmgr"))

    def test_json_list_instead_of_object_is_tolerated(self) -> None:
        import pkgmgr.core.version.installed as mod

        # Valid JSON, wrong shape: data.get() raises AttributeError on a list.
        with (
            patch.object(mod.shutil, "which", return_value="/usr/bin/nix"),
            patch.object(mod, "_run_nix", return_value=(0, '["a", "b"]', "")),
        ):
            self.assertIsNone(mod.get_installed_nix_profile_version("pkgmgr"))


class TestNixProfileParsingDegradation(unittest.TestCase):
    """nix profile normalizer and list reader"""

    def test_coerce_index_rejects_oversized_digit_strings(self) -> None:
        from pkgmgr.actions.install.installers.nix.profile.normalizer import (
            coerce_index,
        )

        # str.isdigit() accepts characters int() refuses, e.g. superscripts.
        self.assertIsNone(coerce_index("²³", {}))
        self.assertIsNone(coerce_index("name-x", {"index": "²"}))

    def test_profile_list_skips_unparsable_index(self) -> None:
        from pkgmgr.actions.install.installers.nix.profile_list import (
            NixProfileListReader,
        )

        runner = MagicMock()
        runner.run.return_value = SimpleNamespace(
            returncode=0,
            stdout="  7 /nix/store/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-demo\n",
        )
        entries = NixProfileListReader(runner).entries(SimpleNamespace())
        self.assertEqual(
            entries,
            [(7, "/nix/store/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa-demo")],
        )


class TestReleaseFileDegradation(unittest.TestCase):
    """src/pkgmgr/actions/release/files/*"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = self.tmp.name

    def test_undecodable_flake_is_reported_not_raised(self) -> None:
        from pkgmgr.actions.release.files.flake import update_flake_version

        path = _write(os.path.join(self.dir, "flake.nix"), BAD_UTF8)
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            update_flake_version(path, "2.0.0")
        self.assertIn("Could not read flake.nix", buf.getvalue())

    def test_undecodable_pkgbuild_is_reported_not_raised(self) -> None:
        from pkgmgr.actions.release.files.pkgbuild import update_pkgbuild_version

        path = _write(os.path.join(self.dir, "PKGBUILD"), BAD_UTF8)
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            update_pkgbuild_version(path, "2.0.0")
        self.assertIn("Could not read PKGBUILD", buf.getvalue())

    def test_undecodable_spec_is_reported_not_raised(self) -> None:
        from pkgmgr.actions.release.files.rpm_spec import update_spec_version

        path = _write(os.path.join(self.dir, "pkg.spec"), BAD_UTF8)
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            update_spec_version(path, "2.0.0")
        self.assertIn("Could not read spec file", buf.getvalue())


class TestMirrorConfigDegradation(unittest.TestCase):
    """src/pkgmgr/actions/mirror/merge_cmd.py"""

    def test_broken_user_config_yields_empty_mapping(self) -> None:
        from pkgmgr.actions.mirror.merge_cmd import _load_user_config

        with tempfile.TemporaryDirectory() as tmp:
            path = _write(os.path.join(tmp, "config.yaml"), "a: [1,\nb: }{")
            self.assertEqual(_load_user_config(path), {})

            undecodable = _write(os.path.join(tmp, "bad.yaml"), BAD_UTF8)
            self.assertEqual(_load_user_config(undecodable), {})


class TestRepositoryDeleteDegradation(unittest.TestCase):
    """src/pkgmgr/actions/repository/delete.py"""

    def test_rmtree_failure_is_reported_not_raised(self) -> None:
        import pkgmgr.actions.repository.delete as mod

        repo = {"provider": "github.com", "account": "a", "repository": "r"}
        buf = io.StringIO()
        with (
            patch.object(mod.shutil, "rmtree", side_effect=OSError("device busy")),
            patch.object(mod.os.path, "exists", return_value=True),
            patch.object(mod, "get_repo_dir", return_value="/repos/a/r"),
            patch("builtins.input", return_value="y"),
            patch("sys.stdout", buf),
        ):
            mod.delete_repos([repo], "/repos", [repo], preview=False)
        self.assertIn("Error deleting", buf.getvalue())


class TestInkDegradation(unittest.TestCase):
    """src/pkgmgr/core/command/ink.py"""

    def test_chmod_failure_is_reported_not_raised(self) -> None:
        import pkgmgr.core.command.ink as mod

        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = os.path.join(tmp, "p", "a", "repo")
            bin_dir = os.path.join(tmp, "bin")
            os.makedirs(repo_dir)
            _write(os.path.join(repo_dir, "main.py"), "print()\n")
            repo = {
                "provider": "p",
                "account": "a",
                "repository": "repo",
                "command": os.path.join(repo_dir, "main.py"),
            }
            buf = io.StringIO()
            with (
                patch.object(mod.os, "chmod", side_effect=OSError("read-only fs")),
                patch("sys.stdout", buf),
            ):
                mod.create_ink(
                    repo,
                    tmp,
                    bin_dir,
                    [repo],
                    quiet=False,
                    preview=False,
                )
            self.assertIn("Failed to set permissions", buf.getvalue())


class TestHttpClientDegradation(unittest.TestCase):
    """src/pkgmgr/core/remote_provisioning/http/client.py"""

    def test_non_json_body_is_returned_as_text(self) -> None:
        from pkgmgr.core.remote_provisioning.http.client import HttpClient

        resp = MagicMock()
        resp.read.return_value = b"<html>not json</html>"
        resp.status = 200
        resp.__enter__ = lambda s: s
        resp.__exit__ = lambda *a: False

        with patch(
            "pkgmgr.core.remote_provisioning.http.client.urllib.request.urlopen",
            return_value=resp,
        ):
            out = HttpClient().request_json("GET", "https://example.invalid/x")
        self.assertIsNone(out.json)
        self.assertIn("not json", out.text)

    def test_unreadable_error_body_degrades_to_empty_string(self) -> None:
        from pkgmgr.core.remote_provisioning.http.client import HttpClient
        from pkgmgr.core.remote_provisioning.http.errors import HttpError

        class BrokenBody(io.RawIOBase):
            def read(self, *args):
                raise OSError("socket closed")

        err = urllib.error.HTTPError(
            url="https://example.invalid/x",
            code=503,
            msg="nope",
            hdrs={},
            fp=BrokenBody(),
        )
        with (
            patch(
                "pkgmgr.core.remote_provisioning.http.client.urllib.request.urlopen",
                side_effect=err,
            ),
            self.assertRaises(HttpError) as ctx,
        ):
            HttpClient().request_json("GET", "https://example.invalid/x")
        self.assertEqual(ctx.exception.status, 503)
        self.assertEqual(ctx.exception.body, "")


class TestProviderRegistryDegradation(unittest.TestCase):
    """src/pkgmgr/core/remote_provisioning/registry.py"""

    def test_misbehaving_provider_is_skipped(self) -> None:
        from pkgmgr.core.remote_provisioning.registry import ProviderRegistry

        class Broken:
            def can_handle(self, host):
                raise TypeError("host is not what I expected")

        class Good:
            def can_handle(self, host):
                return True

        good = Good()
        self.assertIs(ProviderRegistry(providers=[Broken(), good]).resolve("x"), good)

    def test_registry_returns_none_when_all_providers_break(self) -> None:
        from pkgmgr.core.remote_provisioning.registry import ProviderRegistry

        class Broken:
            def can_handle(self, host):
                raise AttributeError("nope")

        self.assertIsNone(ProviderRegistry(providers=[Broken()]).resolve("x"))


class TestCredentialProviderDegradation(unittest.TestCase):
    """gh token provider and token validation"""

    def test_missing_gh_binary_returns_none(self) -> None:
        import pkgmgr.core.credentials.providers.gh as mod
        from pkgmgr.core.credentials.types import TokenRequest

        req = TokenRequest(provider_kind="github", host="github.com", owner=None)
        with (
            patch.object(mod.shutil, "which", return_value="/usr/bin/gh"),
            patch.object(
                mod.subprocess,
                "check_output",
                side_effect=FileNotFoundError("gh vanished"),
            ),
        ):
            self.assertIsNone(mod.GhTokenProvider().get(req))

    def test_failing_gh_command_returns_none(self) -> None:
        import pkgmgr.core.credentials.providers.gh as mod
        from pkgmgr.core.credentials.types import TokenRequest

        req = TokenRequest(provider_kind="github", host="github.com", owner=None)
        with (
            patch.object(mod.shutil, "which", return_value="/usr/bin/gh"),
            patch.object(
                mod.subprocess,
                "check_output",
                side_effect=subprocess.CalledProcessError(1, ["gh"]),
            ),
        ):
            self.assertIsNone(mod.GhTokenProvider().get(req))

    def test_unreachable_host_makes_token_invalid(self) -> None:
        import pkgmgr.core.credentials.validate as mod

        with patch.object(
            mod.urllib.request, "urlopen", side_effect=urllib.error.URLError("no route")
        ):
            self.assertFalse(mod.validate_token("github", "github.com", "tok"))

    def test_non_json_validation_body_makes_token_invalid(self) -> None:
        import pkgmgr.core.credentials.validate as mod

        resp = MagicMock()
        resp.status = 200
        resp.read.return_value = b"<html>gateway</html>"
        resp.__enter__ = lambda s: s
        resp.__exit__ = lambda *a: False
        with patch.object(mod.urllib.request, "urlopen", return_value=resp):
            self.assertFalse(mod.validate_token("github", "github.com", "tok"))


class TestConfigLoadDegradation(unittest.TestCase):
    """src/pkgmgr/core/config/load.py"""

    def test_missing_pkgmgr_package_yields_empty_defaults(self) -> None:
        import builtins

        from pkgmgr.core.config.load import _load_defaults_from_package_or_project

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "pkgmgr":
                raise ImportError("not installed")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=fake_import):
            self.assertEqual(
                _load_defaults_from_package_or_project(),
                {"directories": {}, "repositories": []},
            )


class TestArchPkgbuildDegradation(unittest.TestCase):
    """src/pkgmgr/actions/install/installers/os_packages/arch_pkgbuild.py"""

    def test_missing_geteuid_does_not_break_supports(self) -> None:
        import pkgmgr.actions.install.installers.os_packages.arch_pkgbuild as mod

        ctx = SimpleNamespace(repo_dir="/repo")
        with (
            patch.object(mod.os, "geteuid", side_effect=OSError("no euid here")),
            patch.object(mod.shutil, "which", return_value=None),
        ):
            self.assertFalse(mod.ArchPkgbuildInstaller().supports(ctx))


class TestCliDirectoryResolutionDegradation(unittest.TestCase):
    """CLI commands resolving repository directories from malformed config"""

    def test_dispatch_skips_malformed_repository_entries(self) -> None:
        import pkgmgr.cli.dispatch as mod

        ctx = SimpleNamespace(
            all_repositories=[{"provider": "github.com"}],
            repositories_base_dir="/repos",
        )
        with patch.object(mod, "get_repo_dir", side_effect=KeyError("account")):
            self.assertEqual(mod._select_repo_for_current_directory(ctx), [])

    def test_proxy_skips_malformed_repository_entries(self) -> None:
        import pkgmgr.cli.proxy as mod

        ctx = SimpleNamespace(
            all_repositories=[{"provider": "github.com"}],
            repositories_base_dir="/repos",
        )
        with patch.object(mod, "get_repo_dir", side_effect=TypeError("bad entry")):
            self.assertEqual(mod._select_repo_for_current_directory(ctx), [])


class TestGitTagQueryDegradation(unittest.TestCase):
    """changelog and version CLI reading git tags outside a repository"""

    def test_changelog_reports_unreadable_tags(self) -> None:
        import pkgmgr.cli.commands.changelog as mod
        from pkgmgr.core.git import GitRunError

        with tempfile.TemporaryDirectory() as tmp:
            ctx = SimpleNamespace(
                all_repositories=[],
                repositories_base_dir=tmp,
                config_merged={},
            )
            repo = {"directory": tmp, "repository": "demo"}
            buf = io.StringIO()
            with (
                patch.object(mod, "get_tags", side_effect=GitRunError("not a git repo")),
                patch.object(mod, "get_repo_identifier", return_value="demo"),
                patch.object(mod, "generate_changelog", return_value=""),
                patch("sys.stdout", buf),
            ):
                mod.handle_changelog(SimpleNamespace(command="show"), ctx, [repo])
            self.assertIn("Could not read git tags", buf.getvalue())


if __name__ == "__main__":
    unittest.main()


class TestReleaseFileWriteDegradation(unittest.TestCase):
    """release file updaters that read or write packaging metadata"""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = self.tmp.name

    def test_undecodable_changelog_is_reported_and_rewritten(self) -> None:
        from pkgmgr.actions.release.files.changelog_md import update_changelog

        path = _write(os.path.join(self.dir, "CHANGELOG.md"), BAD_UTF8)
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            update_changelog(path, "2.0.0", message="Fix things", preview=True)
        self.assertIn("Could not read existing CHANGELOG.md", buf.getvalue())

    def test_undecodable_debian_changelog_is_reported(self) -> None:
        from pkgmgr.actions.release.files.debian import update_debian_changelog

        path = _write(os.path.join(self.dir, "changelog"), BAD_UTF8)
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            update_debian_changelog(path, "demo", "2.0.0", message="Fix", preview=False)
        self.assertIn("Could not read debian/changelog", buf.getvalue())

    def test_undecodable_spec_changelog_is_reported(self) -> None:
        from pkgmgr.actions.release.files.rpm_changelog import update_spec_changelog

        path = _write(os.path.join(self.dir, "pkg.spec"), BAD_UTF8)
        buf = io.StringIO()
        with patch("sys.stdout", buf):
            update_spec_changelog(path, "demo", "2.0.0", message="Fix", preview=False)
        self.assertIn("Could not read spec file for changelog update", buf.getvalue())

    def test_unwritable_spec_changelog_is_reported(self) -> None:
        import pkgmgr.actions.release.files.rpm_changelog as mod

        path = _write(
            os.path.join(self.dir, "pkg.spec"),
            "Name: demo\nVersion: 1.0.0\n%changelog\n",
        )
        real_open = open
        buf = io.StringIO()

        def failing_open(file, mode="r", *args, **kwargs):
            if "w" in mode:
                raise OSError("disk full")
            return real_open(file, mode, *args, **kwargs)

        with patch("builtins.open", side_effect=failing_open), patch("sys.stdout", buf):
            mod.update_spec_changelog(path, "demo", "2.0.0", message="Fix")
        self.assertIn("Failed to write updated spec changelog", buf.getvalue())


class TestTemplateImportDegradation(unittest.TestCase):
    """src/pkgmgr/actions/repository/create/templates.py"""

    def test_module_records_missing_jinja2(self) -> None:
        import pkgmgr.actions.repository.create.templates as mod

        self.assertTrue(hasattr(mod, "_JINJA_IMPORT_ERROR"))
        if mod.Environment is None:
            self.assertIsNotNone(mod._JINJA_IMPORT_ERROR)
        else:
            self.assertIsNone(mod._JINJA_IMPORT_ERROR)


class TestCliRepoDirDegradation(unittest.TestCase):
    """CLI handlers resolving repo dirs from malformed entries"""

    def _ctx(self):
        return SimpleNamespace(
            all_repositories=[],
            repositories_base_dir="/repos",
            binaries_dir="/bin",
            config_merged={},
        )

    def test_changelog_skips_unresolvable_directory(self) -> None:
        import pkgmgr.cli.commands.changelog as mod

        buf = io.StringIO()
        with (
            patch.object(mod, "get_repo_dir", side_effect=KeyError("account")),
            patch.object(mod, "get_repo_identifier", return_value="demo"),
            patch("sys.stdout", buf),
        ):
            mod.handle_changelog(
                SimpleNamespace(range=""), self._ctx(), [{"repository": "demo"}]
            )
        self.assertIn("Skipped", buf.getvalue())

    def test_version_skips_unresolvable_directory(self) -> None:
        import pkgmgr.cli.commands.version as mod

        buf = io.StringIO()
        with (
            patch.object(mod, "get_repo_dir", side_effect=TypeError("bad entry")),
            patch.object(mod, "get_repo_identifier", return_value="demo"),
            patch("sys.stdout", buf),
        ):
            mod.handle_version(
                SimpleNamespace(), self._ctx(), [{"repository": "demo"}]
            )
        self.assertIn("Skipped", buf.getvalue())

    def test_release_skips_unresolvable_directory(self) -> None:
        import pkgmgr.cli.commands.release as mod

        buf = io.StringIO()
        with (
            patch.object(mod, "get_repo_dir", side_effect=AttributeError("nope")),
            patch.object(mod, "get_repo_identifier", return_value="demo"),
            patch("sys.stdout", buf),
        ):
            mod.handle_release(
                SimpleNamespace(list=False), self._ctx(), [{"repository": "demo"}]
            )
        self.assertIn("failed to resolve directory", buf.getvalue())

    def test_repos_path_reports_unresolvable_directory(self) -> None:
        import pkgmgr.cli.commands.repos as mod

        buf = io.StringIO()
        with (
            patch.object(
                mod, "_resolve_repository_directory", side_effect=ValueError("bad")
            ),
            patch("sys.stdout", buf),
        ):
            mod.handle_repos_command(
                SimpleNamespace(command="path"), self._ctx(), [{"repository": "demo"}]
            )
        self.assertIn("Could not resolve directory", buf.getvalue())

    def test_version_reports_unreadable_tags(self) -> None:
        import pkgmgr.cli.commands.version as mod
        from pkgmgr.core.git import GitRunError

        with tempfile.TemporaryDirectory() as tmp:
            buf = io.StringIO()
            with (
                patch.object(mod, "get_tags", side_effect=GitRunError("no repo")),
                patch.object(mod, "get_repo_identifier", return_value="demo"),
                patch("sys.stdout", buf),
            ):
                mod.handle_version(
                    SimpleNamespace(), self._ctx(), [{"directory": tmp}]
                )
            self.assertIn("Could not read git tags", buf.getvalue())


class TestInkAliasDegradation(unittest.TestCase):
    """alias symlink creation in src/pkgmgr/core/command/ink.py"""

    def test_alias_symlink_failure_is_reported_not_raised(self) -> None:
        import pkgmgr.core.command.ink as mod

        with tempfile.TemporaryDirectory() as tmp:
            repo_dir = os.path.join(tmp, "p", "a", "repo")
            bin_dir = os.path.join(tmp, "bin")
            os.makedirs(repo_dir)
            command = _write(os.path.join(repo_dir, "main.py"), "print()\n")
            repo = {
                "provider": "p",
                "account": "a",
                "repository": "repo",
                "command": command,
                "alias": "demo-alias",
            }
            buf = io.StringIO()
            real_symlink = os.symlink
            calls = {"n": 0}

            def flaky_symlink(src, dst, **kwargs):
                calls["n"] += 1
                if calls["n"] > 1:
                    raise OSError("alias target is on a read-only mount")
                return real_symlink(src, dst, **kwargs)

            with patch.object(mod.os, "symlink", side_effect=flaky_symlink), patch(
                "sys.stdout", buf
            ):
                mod.create_ink(repo, tmp, bin_dir, [repo], quiet=False, preview=False)
            self.assertIn("Error creating alias", buf.getvalue())


class TestNixIndexParsingDegradation(unittest.TestCase):
    """remaining int() guards in the nix profile helpers"""

    def test_coerce_index_rejects_oversized_trailing_number(self) -> None:
        from pkgmgr.actions.install.installers.nix.profile.normalizer import (
            coerce_index,
        )

        # Matches the "<name>-<digits>" branch, but int() refuses digit strings
        # longer than sys.get_int_max_str_digits().
        self.assertIsNone(coerce_index("pkg-" + "9" * 5000, {}))

    def test_profile_list_skips_oversized_index(self) -> None:
        from pkgmgr.actions.install.installers.nix.profile_list import (
            NixProfileListReader,
        )

        runner = MagicMock()
        runner.run.return_value = SimpleNamespace(
            returncode=0,
            stdout="  " + "9" * 5000 + " /nix/store/"
            + "a" * 32 + "-demo\n",
        )
        self.assertEqual(NixProfileListReader(runner).entries(SimpleNamespace()), [])


class TestTomliFallbackDegradation(unittest.TestCase):
    """second tomllib import guard in version/source.py"""

    @unittest.skipUnless(HAS_TOMLI, "tomli is not installed")
    def test_project_name_falls_back_to_tomli(self) -> None:
        import builtins

        from pkgmgr.core.version.source import read_pyproject_project_name

        with tempfile.TemporaryDirectory() as tmp:
            _write(os.path.join(tmp, "pyproject.toml"), '[project]\nname = "demo"\n')
            real_import = builtins.__import__

            def fake_import(name, *args, **kwargs):
                if name == "tomllib":
                    raise ImportError("no tomllib")
                return real_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=fake_import):
                self.assertEqual(read_pyproject_project_name(tmp), "demo")
