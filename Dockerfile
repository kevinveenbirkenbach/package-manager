FROM archlinux:latest

# 1) System basis + Nix
RUN pacman -Syu --noconfirm \
    && pacman -S --noconfirm --needed \
        base-devel \
        git \
        nix \
    && pacman -Scc --noconfirm

# 2) Unprivileged user for building Arch packages
RUN useradd -m builder
WORKDIR /build

# 3) Only PKGBUILD rein, um dein Wrapper-Paket zu bauen
COPY PKGBUILD .

RUN chown -R builder:builder /build \
    && su builder -c "makepkg -s --noconfirm --clean" \
    && pacman -U --noconfirm package-manager-*.pkg.tar.* \
    && rm -rf /build

# 4) Projekt-Quellen für Tests in den Container kopieren
WORKDIR /src
COPY . .

# pkgmgr (Arch-Package) ist installiert und ruft nix run auf.
ENTRYPOINT ["pkgmgr"]
CMD ["--help"]
