Name:           package-manager
Version:        1.8.5
Release:        1%{?dist}
Summary:        Wrapper that runs Kevin's package-manager via Nix flake

License:        MIT
URL:            https://github.com/kevinveenbirkenbach/package-manager
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

# NOTE:
# Nix is a runtime requirement, but it is *not* declared here as a hard
# RPM dependency, because many distributions do not ship a "nix" RPM.
# Instead, Nix is installed and initialized by nix/init.sh, which is
# called in the %post scriptlet below.

%description
This package provides the `pkgmgr` command, which runs Kevin's package
manager via a local Nix flake:

  nix run /usr/lib/package-manager#pkgmgr -- ...

Nix is a runtime requirement and is installed/initialized by the
nix/init.sh helper during package installation if it is not yet
available on the system.

%prep
%setup -q

%build
# No build step required; we ship the project tree as-is.
:

%install
rm -rf %{buildroot}

install -d %{buildroot}%{_bindir}
install -d %{buildroot}/usr/lib/package-manager

# Copy full project source into /usr/lib/package-manager
cp -a . %{buildroot}/usr/lib/package-manager/

# Wrapper
install -m0755 scripts/launcher.sh %{buildroot}%{_bindir}/pkgmgr

# Nix bootstrap (init + lib)
install -d %{buildroot}/usr/lib/package-manager/nix
cp -a scripts/nix/* %{buildroot}/usr/lib/package-manager/nix/
chmod 0755 %{buildroot}/usr/lib/package-manager/nix/init.sh

# Remove packaging-only and development artefacts from the installed tree
rm -rf \
  %{buildroot}/usr/lib/package-manager/PKGBUILD \
  %{buildroot}/usr/lib/package-manager/Dockerfile \
  %{buildroot}/usr/lib/package-manager/debian \
  %{buildroot}/usr/lib/package-manager/.git \
  %{buildroot}/usr/lib/package-manager/.github \
  %{buildroot}/usr/lib/package-manager/tests \
  %{buildroot}/usr/lib/package-manager/.gitignore \
  %{buildroot}/usr/lib/package-manager/__pycache__ \
  %{buildroot}/usr/lib/package-manager/.gitkeep || true

%post
/usr/lib/package-manager/nix/init.sh || echo ">>> ERROR: /usr/lib/package-manager/nix/init.sh not found or not executable."

%postun
echo ">>> package-manager removed. Nix itself was not removed."

%files
%doc README.md
%license LICENSE
%{_bindir}/pkgmgr
/usr/lib/package-manager/

%changelog
* Wed Dec 17 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 1.8.5-1
- * Clearer Git error handling, especially when a directory is not a Git repository.
* More reliable repository verification with improved commit and GPG signature checks.
* Better error messages and overall robustness when working with Git-based workflows.

* Wed Dec 17 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 1.9.0-1
- Automated release.

* Wed Dec 17 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 1.8.4-1
- * Made pkgmgr’s base-layer role explicit by standardizing the Docker/CI mount path to *`/opt/src/pkgmgr`*.

* Tue Dec 16 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 1.8.3-1
- MIRRORS now supports plain URL entries, ensuring metadata-only sources like PyPI are recorded without ever being added to the Git configuration.

* Tue Dec 16 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 1.8.2-1
- * ***pkgmgr tools code*** is more robust and predictable: it now fails early with clear errors if VS Code is not installed or a repository is not yet identified.

* Tue Dec 16 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 1.8.1-1
- * Improved stability and consistency of all Git operations (clone, pull, push, release, branch handling) with clearer error messages and predictable preview behavior.
* Mirrors are now handled cleanly: only valid Git remotes are used for Git operations, while non-Git URLs (e.g. PyPI) are excluded, preventing broken or confusing repository configs.
* GitHub authentication is more robust: tokens are automatically resolved via the GitHub CLI (`gh`), invalid stored tokens are replaced, and interactive prompts occur only when necessary.
* Repository creation and release workflows are more reliable, producing cleaner Git configurations and more predictable version handling.

* Mon Dec 15 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 1.8.0-1
- *** New Features: ***
- **Silent Updates**: You can now use the `--silent` flag during installs and updates to suppress error messages for individual repositories and get a single summary at the end. This ensures the process continues even if some repositories fail, while still preserving interactive checks when not in silent mode.
- **Repository Scaffolding**: The process for creating new repositories has been improved. You can now use templates to scaffold repositories with a preview and automatic mirror setup.

*** Bug Fixes: ***
- **Pip Installation**: Pip is now installed automatically on all supported systems. This includes `python-pip` for Arch and `python3-pip` for CentOS, Debian, Fedora, and Ubuntu, ensuring that pip is available for Python package installations.
- **Pacman Keyring**: Fixed an issue on Arch Linux where package installation would fail due to missing keys. The pacman keyring is now properly initialized before installing packages.

* Mon Dec 15 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 1.7.2-1
- * Git mirrors are now resolved consistently (origin → MIRRORS file → config → default).
* The `origin` remote is always enforced to use the primary URL for both fetch and push.
* Additional mirrors are added as extra push targets without duplication.
* Local and remote mirror setup behaves more predictably and consistently.
* Improved test coverage ensures stable origin and push URL handling.

* Sun Dec 14 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 1.7.1-1
- Patched package-manager to kpmx to publish on pypi

* Sun Dec 14 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 1.7.0-1
- * New *pkgmgr publish* command to publish repository artifacts to PyPI based on the *MIRRORS* file.
* Automatically selects the current repository when no explicit selection is given.
* Publishes only when a semantic version tag is present on *HEAD*; otherwise skips with a clear info message.
* Supports non-interactive mode for CI environments via *--non-interactive*.

* Sun Dec 14 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 1.6.4-1
- * Improved reliability of Nix installs and updates, including automatic resolution of profile conflicts and better handling of GitHub 403 rate limits.
* More stable launcher behavior in packaged and virtual-env setups.
* Enhanced mirror and remote handling: repository owner/name are derived from URLs, with smoother provisioning and clearer credential handling.
* More reliable releases and artifacts due to safer CI behavior when no version tag is present.

* Sun Dec 14 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 1.6.3-1
- ***Fixed:*** Corrected repository path resolution so release and version logic consistently use the canonical packaging/* layout, preventing changelog and packaging files from being read or updated from incorrect locations.

* Wed Dec 10 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 0.9.1-1
- * Refactored installer: new `venv-create.sh`, cleaner root/user setup flow, updated README with architecture map.
* Split virgin tests into root/user workflows; stabilized Nix installer across distros; improved test scripts with dynamic distro selection and isolated Nix stores.
* Fixed repository directory resolution; improved `pkgmgr path` and `pkgmgr shell`; added full unit/E2E coverage.
* Removed deprecated files and updated `.gitignore`.

* Wed Dec 10 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 0.9.0-1
- Introduce a virgin Arch-based Nix flake E2E workflow that validates pkgmgr’s full flake installation path using shared caches for faster and reproducible CI runs.

* Wed Dec 10 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 0.8.0-1
- **v0.7.15 — Installer & Command Resolution Improvements**

* Introduced a unified **layer-based installer pipeline** with clear precedence (OS-packages, Nix, Python, Makefile).
* Reworked installer structure and improved Python/Nix/Makefile installers, including isolated Python venvs and refined flake-output handling.
* Fully rewrote **command resolution** with stronger typing, safer fallbacks, and explicit support for `command: null` to mark library-only repositories.
* Added extensive **unit and integration tests** for installer capability ordering, command resolution, and Nix/Python installer behavior.
* Expanded documentation with capability hierarchy diagrams and scenario matrices.
* Removed deprecated repository entries and obsolete configuration files.

* Wed Dec 10 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 0.7.14-1
- Fixed the clone-all integration test so that `SystemExit(0)` from the proxy is treated as a successful command instead of a failure.

* Wed Dec 10 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 0.7.13-1
- Automated release.

* Tue Dec 09 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 0.7.12-1
- Fixed self refering alias during setup

* Tue Dec 09 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 0.7.11-1
- test: fix installer unit tests for OS packages and Nix dev shell

* Tue Dec 09 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 0.7.10-1
- Fixed test_install_pkgmgr_shallow.py

* Tue Dec 09 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 0.7.9-1
- 'main' and 'master' are now both accepted as branches for branch close merge

* Tue Dec 09 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 0.7.8-1
- Missing pyproject.toml doesn't lead to an error during release

* Tue Dec 09 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 0.7.7-1
- Added TEST_PATTERN parameter to execute dedicated tests

* Tue Dec 09 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 0.7.6-1
- Fixed pull --preview bug in e2e test

* Tue Dec 09 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 0.7.5-1
- Fixed wrong directory permissions for nix

* Tue Dec 09 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 0.7.4-1
- Fixed missing build in test workflow -> Tests pass now

* Tue Dec 09 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 0.7.3-1
- Fixed bug: Ignored packages are now ignored

* Tue Dec 09 2025 Kevin Veen-Birkenbach <kevin@veen.world> - 0.7.2-1
- Implemented Changelog Support for Fedora and Debian

* Sat Dec 06 2025 Kevin Veen-Birkenbach <info@veen.world> - 0.1.1-1
- Initial RPM packaging for package-manager
