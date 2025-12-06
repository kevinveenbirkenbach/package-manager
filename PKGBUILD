# Maintainer: Kevin Veen-Birkenbach <info@veen.world>

pkgname=package-manager
pkgver=0.1.1
pkgrel=1
pkgdesc="Wrapper that runs Kevin's package-manager via Nix flake."
arch=('any')
url="https://github.com/kevinveenbirkenbach/package-manager"
license=('MIT')

depends=('nix')

install=${pkgname}.install

source=('scripts/pkgmgr-wrapper.sh'
        'scripts/init-nix.sh')
sha256sums=('SKIP'
            'SKIP')

build() {
  :
}

package() {
  install -d "$pkgdir/usr/bin"
  install -d "$pkgdir/usr/lib/package-manager"

  # Wrapper
  install -m0755 "scripts/pkgmgr-wrapper.sh" "$pkgdir/usr/bin/pkgmgr"

  # Shared Nix init script
  install -m0755 "scripts/init-nix.sh" "$pkgdir/usr/lib/package-manager/init-nix.sh"
}
