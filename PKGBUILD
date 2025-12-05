# Maintainer: Kevin Veen-Birkenbach <info@veen.world>

pkgname=package-manager
pkgver=0.1.0
pkgrel=1
pkgdesc="A configurable Python tool to manage multiple repositories via Bash and automate common Git operations."
arch=('any')
url="https://github.com/kevinveenbirkenbach/package-manager"
license=('MIT')

depends=(
  'python'
  'python-yaml'
  'git'
  'bash'
)

makedepends=(
  'python-build'
  'python-installer'
  'python-wheel'
  'python-setuptools'
)

source=("$pkgname-$pkgver.tar.gz::$url/archive/refs/tags/v$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
  cd "$srcdir/$pkgname-$pkgver"
  python -m build --wheel --no-isolation
}

package() {
  cd "$srcdir/$pkgname-$pkgver"
  python -m installer --destdir="$pkgdir" dist/*.whl

  # Optional: add pkgmgr executable symlink
  install -Dm755 main.py "$pkgdir/usr/bin/pkgmgr"
}
