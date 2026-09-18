# syntax=docker/dockerfile:1

# One image, built on the distribution base published by
# https://github.com/kevinveenbirkenbach/base-images, which owns the build
# dependencies this used to install in a `virgin` stage of its own.
#
# hadolint ignore=DL3006,InvalidDefaultArgInFrom
# BASE_IMAGE carries no default on purpose: a default would build one
# distribution's image under another distribution's tag whenever the build arg
# is forgotten. scripts/build/base.sh is the only place that resolves it.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

SHELL ["/bin/bash", "-lc"]

WORKDIR /build

COPY . .

RUN set -eu; \
  echo "Building and installing package-manager via make install..."; \
  make install; \
  rm -rf /build

COPY scripts/docker/entry.sh /usr/local/bin/docker-entry.sh

WORKDIR /opt/src/pkgmgr
ENTRYPOINT ["/usr/local/bin/docker-entry.sh"]
CMD ["pkgmgr", "--help"]
