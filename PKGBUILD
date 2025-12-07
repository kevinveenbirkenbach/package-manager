# Maintainer: Kevin Veen-Birkenbach <info@veen.world>

pkgname=package-manager
pkgver=0.1.1
pkgrel=1
pkgdesc="Local-flake wrapper for Kevin's package-manager (Nix-based)."
arch=('any')
url="https://github.com/kevinveenbirkenbach/package-manager"
license=('MIT')

# Nix is the only runtime dependency; Python is provided by the Nix closure.
depends=('nix')
makedepends=('rsync')

install=${pkgname}.install

# Local source checkout — avoids the tarball requirement.
# This assumes you build the package from inside the main project repository.
source=()
sha256sums=()

# Local source directory name under $srcdir
_srcdir_name="source"

prepare() {
  mkdir -p "$srcdir/$_srcdir_name"

  # Copy the full local tree into $srcdir/source,
  # but avoid makepkg's own directories and the VCS metadata.
  rsync -a \
    --exclude="src" \
    --exclude="pkg" \
    --exclude=".git" \
    "$startdir/" "$srcdir/$_srcdir_name/"
}

build() {
  cd "$srcdir/$_srcdir_name"
  :
}

package() {
  cd "$srcdir/$_srcdir_name"

  # Install the wrapper into /usr/bin
  install -Dm0755 "scripts/pkgmgr-wrapper.sh" \
    "$pkgdir/usr/bin/pkgmgr"

  # Install Nix init helper
  install -Dm0755 "scripts/init-nix.sh" \
    "$pkgdir/usr/lib/package-manager/init-nix.sh"

  # Install the full repository into /usr/lib/package-manager
  mkdir -p "$pkgdir/usr/lib/package-manager"

  # Copy entire project tree from our local source checkout
  cp -a . "$pkgdir/usr/lib/package-manager/"

  # Remove packaging-only and development artefacts from the installed tree
  rm -rf \
    "$pkgdir/usr/lib/package-manager/.git" \
    "$pkgdir/usr/lib/package-manager/.github" \
    "$pkgdir/usr/lib/package-manager/tests" \
    "$pkgdir/usr/lib/package-manager/PKGBUILD" \
    "$pkgdir/usr/lib/package-manager/Dockerfile" \
    "$pkgdir/usr/lib/package-manager/debian" \
    "$pkgdir/usr/lib/package-manager/.gitignore" \
    "$pkgdir/usr/lib/package-manager/__pycache__" \
    "$pkgdir/usr/lib/package-manager/.gitkeep"
}
