Name:           package-manager
Version:        0.1.1
Release:        1%{?dist}
Summary:        Wrapper that runs Kevin's package-manager via Nix flake

License:        MIT
URL:            https://github.com/kevinveenbirkenbach/package-manager
Source0:        %{name}-%{version}.tar.gz

BuildArch:      noarch
Requires:       nix

%description
This package provides the `pkgmgr` command, which runs Kevin's package
manager via a local Nix flake:

  nix run /usr/lib/package-manager#pkgmgr -- ...

Nix is the only runtime dependency and must be initialized on the
system to work correctly.

%prep
%setup -q

%build
# No build step required
:

%install
rm -rf %{buildroot}
install -d %{buildroot}%{_bindir}
install -d %{buildroot}%{_libdir}/package-manager

# Copy full project source into /usr/lib/package-manager
cp -a . %{buildroot}%{_libdir}/package-manager/

# Wrapper
install -m0755 scripts/pkgmgr-wrapper.sh %{buildroot}%{_bindir}/pkgmgr

# Shared Nix init script (ensure it is executable in the installed tree)
install -m0755 scripts/init-nix.sh %{buildroot}%{_libdir}/package-manager/init-nix.sh

# Remove packaging-only and development artefacts from the installed tree
rm -rf \
  %{buildroot}%{_libdir}/package-manager/PKGBUILD \
  %{buildroot}%{_libdir}/package-manager/Dockerfile \
  %{buildroot}%{_libdir}/package-manager/debian \
  %{buildroot}%{_libdir}/package-manager/.git \
  %{buildroot}%{_libdir}/package-manager/.github \
  %{buildroot}%{_libdir}/package-manager/tests \
  %{buildroot}%{_libdir}/package-manager/.gitignore \
  %{buildroot}%{_libdir}/package-manager/__pycache__ \
  %{buildroot}%{_libdir}/package-manager/.gitkeep || true

%post
if [ -x %{_libdir}/package-manager/init-nix.sh ]; then
    %{_libdir}/package-manager/init-nix.sh || true
else
    echo ">>> Warning: %{_libdir}/package-manager/init-nix.sh not found or not executable."
fi

%postun
echo ">>> package-manager removed. Nix itself was not removed."

%files
%doc README.md
%license LICENSE
%{_bindir}/pkgmgr
%{_libdir}/package-manager/

%changelog
* Sat Dec 06 2025 Kevin Veen-Birkenbach <info@veen.world> - 0.1.1-1
- Initial RPM packaging for package-manager
