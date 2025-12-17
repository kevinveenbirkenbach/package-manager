# syntax=docker/dockerfile:1

# ------------------------------------------------------------
# Base image selector — overridden by build args / Makefile
# ------------------------------------------------------------
ARG BASE_IMAGE

# ============================================================
# Target: virgin
# - installs distro deps (incl. make)
# - no pkgmgr build
# - no entrypoint
# ============================================================
FROM ${BASE_IMAGE} AS virgin
SHELL ["/bin/bash", "-lc"]

RUN echo "BASE_IMAGE=${BASE_IMAGE}" && cat /etc/os-release || true

WORKDIR /build

# Copy scripts first so dependency installation can be cached
COPY scripts/installation/ scripts/installation/

# Install distro-specific build dependencies (including make)
RUN bash scripts/installation/dependencies.sh

# Virgin default
CMD ["bash"]


# ============================================================
# Target: full
# - inherits from virgin
# - builds + installs pkgmgr
# - sets entrypoint + default cmd
# ============================================================
FROM virgin AS full

WORKDIR /build

# Copy full repository for build
COPY . .

# Build and install distro-native package-manager package
RUN set -euo pipefail; \
  echo "Building and installing package-manager via make install..."; \
  make install; \
  cd /; rm -rf /build

# Entry point
COPY scripts/docker/entry.sh /usr/local/bin/docker-entry.sh

WORKDIR /opt/src/pkgmgr
ENTRYPOINT ["/usr/local/bin/docker-entry.sh"]
CMD ["pkgmgr", "--help"]
