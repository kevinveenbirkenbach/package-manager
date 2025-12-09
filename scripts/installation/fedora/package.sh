#!/usr/bin/env bash
set -euo pipefail

echo "[fedora/package] Setting up rpmbuild directories..."
mkdir -p /root/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

echo "[fedora/package] Extracting version from package-manager.spec..."
version="$(grep -E '^Version:' package-manager.spec | awk '{print $2}')"
if [[ -z "${version}" ]]; then
  echo "ERROR: Version missing!"
  exit 1
fi

srcdir="package-manager-${version}"
echo "[fedora/package] Preparing source tree: ${srcdir}"
rm -rf "/tmp/${srcdir}"
mkdir -p "/tmp/${srcdir}"
cp -a . "/tmp/${srcdir}/"

echo "[fedora/package] Creating source tarball..."
tar czf "/root/rpmbuild/SOURCES/${srcdir}.tar.gz" -C /tmp "${srcdir}"

echo "[fedora/package] Copying SPEC..."
cp package-manager.spec /root/rpmbuild/SPECS/

echo "[fedora/package] Running rpmbuild..."
cd /root/rpmbuild/SPECS
rpmbuild -bb package-manager.spec

echo "[fedora/package] Installing generated RPM (local, offline, forced reinstall)..."
rpm_path="$(find /root/rpmbuild/RPMS -name 'package-manager-*.rpm' | head -n1)"
if [[ -z "${rpm_path}" ]]; then
  echo "ERROR: RPM not found!"
  exit 1
fi

# Always force (re)install the freshly built RPM, even if the same
# version is already installed. This is what we want in dev/test containers.
rpm -Uvh --replacepkgs --force "${rpm_path}"

rm -rf "/tmp/${srcdir}"

echo "[fedora/package] Done."
