Name:           package-manager
Version:        0.9.1
Release:        1%{?dist}
Summary:        Wrapper that runs Kevin's package-manager via Nix flake

License:        MIT
URL:            https://github.com/kevinveenbirkenbach/package-manager
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch

# NOTE:
# Nix is a runtime requirement, but it is *not* declared here as a hard
# RPM dependency, because many distributions do not ship a "nix" RPM.
# Instead, Nix is installed and initialized by init-nix.sh, which is
# called in the %post scriptlet below.

%description
This package provides the `pkgmgr` command, which runs Kevin's package
manager via a local Nix flake:

  nix run /usr/lib/package-manager#pkgmgr -- ...

Nix is a runtime requirement and is installed/initialized by the
init-nix.sh helper during package installation if it is not yet
available on the system.

%prep
%setup -q

%build
# No build step required; we ship the project tree as-is.
:

%install
rm -rf %{buildroot}
install -d %{buildroot}%{_bindir}
# Install project tree into a fixed, architecture-independent location.
install -d %{buildroot}/usr/lib/package-manager

# Copy full project source into /usr/lib/package-manager
cp -a . %{buildroot}/usr/lib/package-manager/

# Wrapper
install -m0755 scripts/pkgmgr-wrapper.sh %{buildroot}%{_bindir}/pkgmgr

# Shared Nix init script (ensure it is executable in the installed tree)
install -m0755 scripts/init-nix.sh %{buildroot}/usr/lib/package-manager/init-nix.sh

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
/usr/lib/package-manager/init-nix.sh || echo ">>> ERROR: /usr/lib/package-manager/init-nix.sh not found or not executable."

%postun
echo ">>> package-manager removed. Nix itself was not removed."

%files
%doc README.md
%license LICENSE
%{_bindir}/pkgmgr
/usr/lib/package-manager/

%changelog
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
