#!/usr/bin/env bash
set -euo pipefail

echo "[centos/package] Setting up rpmbuild directories..."
mkdir -p /root/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

echo "[centos/package] Extracting version from package-manager.spec..."
version="$(grep -E '^Version:' package-manager.spec | awk '{print $2}')"
if [[ -z "${version}" ]]; then
  echo "ERROR: Version missing!"
  exit 1
fi

srcdir="package-manager-${version}"
echo "[centos/package] Preparing source tree: ${srcdir}"
rm -rf "/tmp/${srcdir}"
mkdir -p "/tmp/${srcdir}"
cp -a . "/tmp/${srcdir}/"

echo "[centos/package] Creating source tarball..."
tar czf "/root/rpmbuild/SOURCES/${srcdir}.tar.gz" -C /tmp "${srcdir}"

echo "[centos/package] Copying SPEC..."
cp package-manager.spec /root/rpmbuild/SPECS/

echo "[centos/package] Running rpmbuild..."
cd /root/rpmbuild/SPECS
rpmbuild -bb package-manager.spec

echo "[centos/package] Installing generated RPM (local, offline, forced reinstall)..."
rpm_path="$(find /root/rpmbuild/RPMS -name 'package-manager-*.rpm' | head -n1)"
if [[ -z "${rpm_path}" ]]; then
  echo "ERROR: RPM not found!"
  exit 1
fi

# ------------------------------------------------------------
# Forced reinstall, always overwrite old version
# ------------------------------------------------------------
echo "[centos/package] Forcing reinstall via rpm -Uvh --replacepkgs --force"
rpm -Uvh --replacepkgs --force "${rpm_path}"

# Keep structure: remove temp directory afterwards
rm -rf "/tmp/${srcdir}"

echo "[centos/package] Done."
