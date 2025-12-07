FROM archlinux:latest

# 1) System basis + Nix
RUN pacman -Syu --noconfirm \
    && pacman -S --noconfirm --needed \
        base-devel \
        git \
        nix \
        rsync \
    && pacman -Scc --noconfirm

ENV NIX_CONFIG="experimental-features = nix-command flakes"

# 2) Unprivileged user for building Arch packages
RUN useradd -m builder

# 3) Build-Stage (optional): einmal aus /build bauen, wenn du magst
WORKDIR /build
COPY . .
RUN chown -R builder:builder /build \
    && su builder -c "cd /build && rm -f package-manager-*.pkg.tar.* && makepkg -sf --noconfirm --clean" \
    && pacman -U --noconfirm package-manager-*.pkg.tar.* \
    && rm -rf /build

# 4) Runtime-Workingdir für das gemountete Repo
WORKDIR /src

# 5) Entry-Script für „always build from /src“
COPY scripts/docker-entry-dev.sh /usr/local/bin/docker-entry-dev.sh
RUN chmod +x /usr/local/bin/docker-entry-dev.sh

ENTRYPOINT ["/usr/local/bin/docker-entry-dev.sh"]
CMD ["--help"]
