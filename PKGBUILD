# Maintainer: Parch Linux Team <parchlinux@gmail.com>
pkgname=parch-grub-fixer
pkgver=1.0.0
pkgrel=1
pkgdesc="Detect Parch Linux installations and repair GRUB or run a full system upgrade"
arch=('any')
url="https://github.com/ParchLinux/parch-grub-fixer"
license=('GPL-3.0-or-later')
depends=('python' 'python-rich' 'grub')
makedepends=('python-build' 'python-installer' 'python-wheel')
source=("$pkgname-$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
    cd "$pkgname-$pkgver"
    python -m build --wheel --no-isolation
}

package() {
    cd "$pkgname-$pkgver"
    python -m installer --destdir="$pkgdir" dist/*.whl
}