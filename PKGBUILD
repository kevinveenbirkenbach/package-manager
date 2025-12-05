# Maintainer: Kevin Veen-Birkenbach <info@veen.world>

pkgname=package-manager
pkgver=0.1.0
pkgrel=1
pkgdesc="Wrapper that runs Kevin's package-manager via Nix flake."
arch=('any')
url="https://github.com/kevinveenbirkenbach/package-manager"
license=('MIT')

# Nix is the only runtime dependency.
depends=('nix')

makedepends=()

source=()
sha256sums=()

build() {
  :
}

package() {
  install -d "$pkgdir/usr/bin"

  cat > "$pkgdir/usr/bin/pkgmgr" << 'EOF'
#!/usr/bin/env bash
set -euo pipefail

# Enable flakes if not already configured.
if [[ -z "${NIX_CONFIG:-}" ]]; then
  export NIX_CONFIG="experimental-features = nix-command flakes"
fi

# Run package-manager via Nix flake
exec nix run "github:kevinveenbirkenbach/package-manager#pkgmgr" -- "$@"
EOF

  chmod 755 "$pkgdir/usr/bin/pkgmgr"
}
