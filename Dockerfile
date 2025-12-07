# ------------------------------------------------------------
# Base image selector — overridden by Makefile
# ------------------------------------------------------------
ARG BASE_IMAGE=archlinux:latest
FROM ${BASE_IMAGE}

# ------------------------------------------------------------
# System base + conditional package installation
# ------------------------------------------------------------
RUN set -e; \
    if [ -f /etc/os-release ]; then . /etc/os-release; else echo "No /etc/os-release found" && exit 1; fi; \
    echo "Detected base image: ${ID:-unknown} (like: ${ID_LIKE:-})"; \
    \
    # --------------------------------------------------------
    # Archlinux: Nix via pacman
    # --------------------------------------------------------
    if [ "$ID" = "arch" ]; then \
        pacman -Syu --noconfirm && \
        pacman -S --noconfirm --needed \
            base-devel \
            git \
            nix \
            rsync && \
        pacman -Scc --noconfirm; \
    \
    # --------------------------------------------------------
    # Debian: Nix installer (single-user, root, no build-users-group)
    # --------------------------------------------------------
    elif [ "$ID" = "debian" ]; then \
        apt-get update && \
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
            ca-certificates \
            curl \
            git \
            python3 \
            python3-venv \
            rsync \
            bash \
            xz-utils && \
        rm -rf /var/lib/apt/lists/* && \
        echo "Preparing /nix + /etc/nix/nix.conf on Debian..." && \
        mkdir -p /nix && chmod 0755 /nix && chown root:root /nix && \
        mkdir -p /etc/nix && printf 'build-users-group =\n' > /etc/nix/nix.conf && \
        echo "Downloading Nix installer on Debian..." && \
        curl -L https://nixos.org/nix/install -o /tmp/nix-install && \
        echo "Installing Nix on Debian (single-user, as root, no build-users-group)..." && \
        HOME=/root NIX_INSTALLER_NO_MODIFY_PROFILE=1 sh /tmp/nix-install --no-daemon && \
        rm -f /tmp/nix-install; \
    \
    # --------------------------------------------------------
    # Ubuntu: Nix installer (single-user, root, no build-users-group)
    # --------------------------------------------------------
    elif [ "$ID" = "ubuntu" ]; then \
        apt-get update && \
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
            ca-certificates \
            curl \
            git \
            tzdata \
            lsb-release \
            python3 \
            python3-venv \
            rsync \
            bash \
            xz-utils && \
        rm -rf /var/lib/apt/lists/* && \
        echo "Preparing /nix + /etc/nix/nix.conf on Ubuntu..." && \
        mkdir -p /nix && chmod 0755 /nix && chown root:root /nix && \
        mkdir -p /etc/nix && printf 'build-users-group =\n' > /etc/nix/nix.conf && \
        echo "Downloading Nix installer on Ubuntu..." && \
        curl -L https://nixos.org/nix/install -o /tmp/nix-install && \
        echo "Installing Nix on Ubuntu (single-user, as root, no build-users-group)..." && \
        HOME=/root NIX_INSTALLER_NO_MODIFY_PROFILE=1 sh /tmp/nix-install --no-daemon && \
        rm -f /tmp/nix-install; \
    \
    # --------------------------------------------------------
    # Fedora: Nix installer (single-user, root, no build-users-group)
    # --------------------------------------------------------
    elif [ "$ID" = "fedora" ]; then \
        dnf -y update && \
        dnf -y install \
            ca-certificates \
            curl \
            git \
            python3 \
            rsync \
            bash \
            xz && \
        dnf clean all && \
        echo "Preparing /nix + /etc/nix/nix.conf on Fedora..." && \
        mkdir -p /nix && chmod 0755 /nix && chown root:root /nix && \
        mkdir -p /etc/nix && printf 'build-users-group =\n' > /etc/nix/nix.conf && \
        echo "Downloading Nix installer on Fedora..." && \
        curl -L https://nixos.org/nix/install -o /tmp/nix-install && \
        echo "Installing Nix on Fedora (single-user, as root, no build-users-group)..." && \
        HOME=/root NIX_INSTALLER_NO_MODIFY_PROFILE=1 sh /tmp/nix-install --no-daemon && \
        rm -f /tmp/nix-install; \
    \
    # --------------------------------------------------------
    # CentOS Stream: Nix installer (single-user, root, no build-users-group)
    # --------------------------------------------------------
    elif [ "$ID" = "centos" ]; then \
        dnf -y update && \
        dnf -y install \
            ca-certificates \
            curl-minimal \
            git \
            python3 \
            rsync \
            bash \
            xz && \
        dnf clean all && \
        echo "Preparing /nix + /etc/nix/nix.conf on CentOS..." && \
        mkdir -p /nix && chmod 0755 /nix && chown root:root /nix && \
        mkdir -p /etc/nix && printf 'build-users-group =\n' > /etc/nix/nix.conf && \
        echo "Downloading Nix installer on CentOS..." && \
        curl -L https://nixos.org/nix/install -o /tmp/nix-install && \
        echo "Installing Nix on CentOS (single-user, as root, no build-users-group)..." && \
        HOME=/root NIX_INSTALLER_NO_MODIFY_PROFILE=1 sh /tmp/nix-install --no-daemon && \
        rm -f /tmp/nix-install; \
    \
    # --------------------------------------------------------
    # Unknown distro
    # --------------------------------------------------------
    else \
        echo "Unsupported base image: ${ID}" && exit 1; \
    fi

# Nix CLI behavior (used later in tests)
ENV NIX_CONFIG="experimental-features = nix-command flakes"
ENV PATH="/root/.nix-profile/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# ------------------------------------------------------------
# Create unprivileged build user (used on Arch for makepkg)
# ------------------------------------------------------------
RUN useradd -m builder

# ------------------------------------------------------------
# Build stage — only active on Arch
# ------------------------------------------------------------
WORKDIR /build
COPY . .

RUN set -e; \
    if [ -f /etc/os-release ]; then . /etc/os-release; fi; \
    if [ "$ID" = "arch" ]; then \
        echo "Running Arch build stage (makepkg)..."; \
        chown -R builder:builder /build && \
        su builder -c "cd /build && rm -f package-manager-*.pkg.tar.* && makepkg -sf --noconfirm --clean"; \
        pacman -U --noconfirm package-manager-*.pkg.tar.*; \
    else \
        echo "Non-Arch base detected — skipping Arch package build."; \
    fi; \
    rm -rf /build

# ------------------------------------------------------------
# Runtime working directory for the mounted repository
# ------------------------------------------------------------
WORKDIR /src

# ------------------------------------------------------------
# Development entry script
# ------------------------------------------------------------
COPY scripts/docker-entry-dev.sh /usr/local/bin/docker-entry-dev.sh
RUN chmod +x /usr/local/bin/docker-entry-dev.sh

ENTRYPOINT ["/usr/local/bin/docker-entry-dev.sh"]
CMD ["--help"]
