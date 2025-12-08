# ------------------------------------------------------------
# Base image selector — overridden by Makefile
# ------------------------------------------------------------
ARG BASE_IMAGE=archlinux:latest
FROM ${BASE_IMAGE}

# ------------------------------------------------------------
# System base + conditional package tool installation
#
# Important:
# - We do NOT install Nix directly here via curl.
# - Nix is installed/initialized by init-nix.sh, which is invoked
#   from the system packaging hooks (Arch .install, Debian postinst,
#   RPM %post).
# ------------------------------------------------------------
RUN set -e; \
    if [ -f /etc/os-release ]; then . /etc/os-release; else echo "No /etc/os-release found" && exit 1; fi; \
    echo "Detected base image: ${ID:-unknown} (like: ${ID_LIKE:-})"; \
    \
    if [ "$ID" = "arch" ]; then \
        pacman -Syu --noconfirm && \
        pacman -S --noconfirm --needed \
            base-devel \
            git \
            rsync \
            curl \
            ca-certificates \
            xz && \
        pacman -Scc --noconfirm; \
    elif [ "$ID" = "debian" ]; then \
        apt-get update && \
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
            build-essential \
            debhelper \
            dpkg-dev \
            git \
            rsync \
            bash \
            curl \
            ca-certificates \
            xz-utils && \
        rm -rf /var/lib/apt/lists/*; \
    elif [ "$ID" = "ubuntu" ]; then \
        apt-get update && \
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
            build-essential \
            debhelper \
            dpkg-dev \
            git \
            tzdata \
            lsb-release \
            rsync \
            bash \
            curl \
            ca-certificates \
            xz-utils && \
        rm -rf /var/lib/apt/lists/*; \
    elif [ "$ID" = "fedora" ]; then \
        dnf -y update && \
        dnf -y install \
            git \
            rsync \
            rpm-build \
            make \
            gcc \
            bash \
            curl \
            ca-certificates \
            xz && \
        dnf clean all; \
    elif [ "$ID" = "centos" ]; then \
        dnf -y update && \
        dnf -y install \
            git \
            rsync \
            rpm-build \
            make \
            gcc \
            bash \
            curl-minimal \
            ca-certificates \
            xz && \
        dnf clean all; \
    else \
        echo "Unsupported base image: ${ID}" && exit 1; \
    fi

# ------------------------------------------------------------
# Nix environment defaults
#
# Nix itself is installed by your system packages (via init-nix.sh).
# Here we only define default configuration options.
# ------------------------------------------------------------
ENV NIX_CONFIG="experimental-features = nix-command flakes"

# ------------------------------------------------------------
# Unprivileged user for Arch package build (makepkg)
# ------------------------------------------------------------
RUN useradd -m builder || true

# ------------------------------------------------------------
# Build and install distro-native package-manager package
#
# - Arch:    PKGBUILD  -> pacman -U
# - Debian:  debhelper -> dpkg-buildpackage -> apt install ./package-manager_*.deb
# - Ubuntu:  same as Debian
# - Fedora:  rpmbuild  -> dnf/dnf5/yum install package-manager-*.rpm
# - CentOS:  rpmbuild  -> dnf/yum install package-manager-*.rpm
#
# Nix is NOT manually installed here; it is handled by init-nix.sh.
# ------------------------------------------------------------
WORKDIR /build
COPY . .

RUN set -e; \
    . /etc/os-release; \
    if [ "$ID" = "arch" ]; then \
        echo 'Building Arch package (makepkg --nodeps)...'; \
        chown -R builder:builder /build; \
        su builder -c "cd /build && rm -f package-manager-*.pkg.tar.* && makepkg --noconfirm --clean --nodeps"; \
        \
        echo 'Installing generated Arch package...'; \
        pacman -U --noconfirm package-manager-*.pkg.tar.*; \
    elif [ "$ID" = "debian" ] || [ "$ID" = "ubuntu" ]; then \
        echo 'Building Debian/Ubuntu package...'; \
        dpkg-buildpackage -us -uc -b; \
        \
        echo 'Installing generated DEB package...'; \
        apt-get update && \
        DEBIAN_FRONTEND=noninteractive apt-get install -y ./../package-manager_*.deb && \
        rm -rf /var/lib/apt/lists/*; \
    elif [ "$ID" = "fedora" ] || [ "$ID" = "centos" ]; then \
        echo 'Setting up rpmbuild dirs...'; \
        mkdir -p /root/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}; \
        \
        echo "Extracting version from package-manager.spec..."; \
        version=$(grep -E '^Version:' /build/package-manager.spec | awk '{print $2}'); \
        if [ -z "$version" ]; then echo 'ERROR: Version missing!' && exit 1; fi; \
        srcdir="package-manager-${version}"; \
        \
        echo "Preparing source tree for RPM: $srcdir"; \
        rm -rf "/tmp/$srcdir"; \
        mkdir -p "/tmp/$srcdir"; \
        cp -a /build/. "/tmp/$srcdir/"; \
        \
        echo "Creating source tarball: /root/rpmbuild/SOURCES/$srcdir.tar.gz"; \
        tar czf "/root/rpmbuild/SOURCES/$srcdir.tar.gz" -C /tmp "$srcdir"; \
        \
        echo 'Copying SPEC...'; \
        cp /build/package-manager.spec /root/rpmbuild/SPECS/; \
        \
        echo 'Running rpmbuild...'; \
        cd /root/rpmbuild/SPECS && rpmbuild -bb package-manager.spec; \
        \
        echo 'Installing generated RPM (local, offline)...'; \
        rpm_path=$(find /root/rpmbuild/RPMS -name "package-manager-*.rpm" | head -n1); \
        if [ -z "$rpm_path" ]; then echo 'ERROR: RPM not found!' && exit 1; fi; \
        \
        if command -v dnf5 >/dev/null 2>&1; then \
            echo 'Using dnf5 to install local RPM (no remote repos)...'; \
            if ! dnf5 install -y --disablerepo='*' "$rpm_path"; then \
                echo 'dnf5 failed, falling back to rpm -i --nodeps'; \
                rpm -i --nodeps "$rpm_path"; \
            fi; \
        elif command -v dnf >/dev/null 2>&1; then \
            echo 'Using dnf to install local RPM (no remote repos)...'; \
            if ! dnf install -y --disablerepo='*' "$rpm_path"; then \
                echo 'dnf failed, falling back to rpm -i --nodeps'; \
                rpm -i --nodeps "$rpm_path"; \
            fi; \
        elif command -v yum >/dev/null 2>&1; then \
            echo 'Using yum to install local RPM (no remote repos)...'; \
            if ! yum localinstall -y --disablerepo='*' "$rpm_path"; then \
                echo 'yum failed, falling back to rpm -i --nodeps'; \
                rpm -i --nodeps "$rpm_path"; \
            fi; \
        else \
            echo 'No dnf/dnf5/yum found, falling back to rpm -i --nodeps...'; \
            rpm -i --nodeps "$rpm_path"; \
        fi; \
        \
        rm -rf "/tmp/$srcdir"; \
    else \
        echo "Unsupported distro: ${ID}"; \
        exit 1; \
    fi; \
    rm -rf /build

# ------------------------------------------------------------
# Runtime working directory and dev entrypoint
# ------------------------------------------------------------
WORKDIR /src

COPY scripts/docker-entry-dev.sh /usr/local/bin/docker-entry-dev.sh
RUN chmod +x /usr/local/bin/docker-entry-dev.sh

ENTRYPOINT ["/usr/local/bin/docker-entry-dev.sh"]
CMD ["--help"]
