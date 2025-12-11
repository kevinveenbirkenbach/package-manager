#!/usr/bin/env bash
set -euo pipefail

echo "[fedora/package] Setting up rpmbuild directories..."
mkdir -p /root/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SPEC_PATH="${PROJECT_ROOT}/packaging/fedora/package-manager.spec"

if [[ ! -f "${SPEC_PATH}" ]]; then
  echo "[fedora/package] ERROR: SPEC file not found: ${SPEC_PATH}"
  exit 1
fi

echo "[fedora/package] Extracting version from package-manager.spec..."
version="$(grep -E '^Version:' "${SPEC_PATH}" | awk '{print $2}')"
if [[ -z "${version}" ]]; then
  echo "ERROR: Version missing!"
  exit 1
fi

srcdir="package-manager-${version}"
echo "[fedora/package] Preparing source tree: ${srcdir}"
rm -rf "/tmp/${srcdir}"
mkdir -p "/tmp/${srcdir}"
cp -a "${PROJECT_ROOT}/." "/tmp/${srcdir}/"

echo "[fedora/package] Creating source tarball..."
tar czf "/root/rpmbuild/SOURCES/${srcdir}.tar.gz" -C /tmp "${srcdir}"

echo "[fedora/package] Copying SPEC..."
cp "${SPEC_PATH}" /root/rpmbuild/SPECS/

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
