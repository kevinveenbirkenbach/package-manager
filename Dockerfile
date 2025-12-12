# ------------------------------------------------------------
# Base image selector — overridden by Makefile
# ------------------------------------------------------------
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

RUN echo "BASE_IMAGE=${BASE_IMAGE}" && \
    cat /etc/os-release || true

# ------------------------------------------------------------
# Nix environment defaults
#
# Nix itself is installed by your system packages (via init-nix.sh).
# Here we only define default configuration options.
# ------------------------------------------------------------
ENV NIX_CONFIG="experimental-features = nix-command flakes"


# ------------------------------------------------------------
# Copy scripts and install distro dependencies
# ------------------------------------------------------------
WORKDIR /build

# Copy only scripts first so dependency installation can run early
COPY scripts/ scripts/
RUN find scripts -type f -name '*.sh' -exec chmod +x {} \;

# ------------------------------------------------------------
# Select distro-specific Docker entrypoint
# ------------------------------------------------------------
# Docker entrypoint (distro-agnostic, nutzt package.sh)
# ------------------------------------------------------------
COPY scripts/docker/entry.sh /usr/local/bin/docker-entry.sh
RUN chmod +x /usr/local/bin/docker-entry.sh

# ------------------------------------------------------------
# Build and install distro-native package-manager package
# via Makefile `install` target
# ------------------------------------------------------------
COPY . .
RUN find scripts -type f -name '*.sh' -exec chmod +x {} \;

RUN set -e; \
    echo "Building and installing package-manager via make install..."; \
    make install; \
    rm -rf /build

# ------------------------------------------------------------
# Runtime working directory and dev entrypoint
# ------------------------------------------------------------
WORKDIR /src

ENTRYPOINT ["/usr/local/bin/docker-entry.sh"]
CMD ["pkgmgr", "--help"]
