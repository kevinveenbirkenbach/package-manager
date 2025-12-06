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
manager via a Nix flake:

  nix run "github:kevinveenbirkenbach/package-manager#pkgmgr" -- ...

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

# Wrapper
install -m0755 scripts/pkgmgr-wrapper.sh %{buildroot}%{_bindir}/pkgmgr

# Shared Nix init script
install -m0755 scripts/init-nix.sh %{buildroot}%{_libdir}/package-manager/init-nix.sh

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
%{_libdir}/package-manager/init-nix.sh

%changelog
* Sat Dec 06 2025 Kevin Veen-Birkenbach <info@veen.world> - 0.1.1-1
- Initial RPM packaging for package-manager
