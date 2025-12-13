.PHONY: install uninstall \
        build build-no-cache build-no-cache-all build-missing \
		delete-volumes purge \
        test test-unit test-e2e test-integration test-env-virtual test-env-nix \
		setup setup-venv setup-nix

# Distro
# Options: arch debian ubuntu fedora centos
DISTROS ?= arch debian ubuntu fedora centos
distro ?= arch
export distro

# ------------------------------------------------------------
# Base images
# (kept for documentation/reference; actual build logic is in scripts/build)
# ------------------------------------------------------------
BASE_IMAGE_ARCH   := archlinux:latest
BASE_IMAGE_DEBIAN := debian:stable-slim
BASE_IMAGE_UBUNTU := ubuntu:latest
BASE_IMAGE_FEDORA := fedora:latest
BASE_IMAGE_CENTOS := quay.io/centos/centos:stream9

# Make them available in scripts
export BASE_IMAGE_ARCH  
export BASE_IMAGE_DEBIAN
export BASE_IMAGE_UBUNTU
export BASE_IMAGE_FEDORA
export BASE_IMAGE_CENTOS

# PYthon Unittest Pattern
TEST_PATTERN	:= test_*.py
export TEST_PATTERN
export PYTHONPATH := src

# ------------------------------------------------------------
# System install
# ------------------------------------------------------------
install:
	@echo "Building and installing distro-native package-manager for this system..."
	@bash scripts/installation/init.sh

# ------------------------------------------------------------
# PKGMGR setup
# ------------------------------------------------------------

# Default: keep current auto-detection behavior
setup: setup-nix setup-venv

# Explicit: developer setup (Python venv + shell RC + install)
setup-venv: setup-nix
	@bash scripts/setup/venv.sh

# Explicit: Nix shell mode (no venv, no RC changes)
setup-nix:
	@bash scripts/setup/nix.sh

# ------------------------------------------------------------
# Docker build targets (delegated to scripts/build)
# ------------------------------------------------------------
build:
	@bash scripts/build/image.sh --target virgin
	@bash scripts/build/image.sh

build-missing-virgin:
	@bash scripts/build/image.sh --target virgin --missing

build-missing: build-missing-virgin
	@bash scripts/build/image.sh --missing

build-no-cache:
	@bash scripts/build/image.sh --target virgin --no-cache
	@bash scripts/build/image.sh --no-cache

build-no-cache-all:
	@set -e; \
	for d in $(DISTROS); do \
	  echo "=== build-no-cache: $$d ==="; \
	  PKGMGR_DISTRO="$$d" $(MAKE) build-no-cache; \
	done

# ------------------------------------------------------------
# Test targets (delegated to scripts/test)
# ------------------------------------------------------------

test-unit: build-missing
	@bash scripts/test/test-unit.sh

test-integration: build-missing
	@bash scripts/test/test-integration.sh

test-e2e: build-missing
	@bash scripts/test/test-e2e.sh

test-env-virtual: build-missing
	@bash scripts/test/test-env-virtual.sh

test-env-nix: build-missing
	@bash scripts/test/test-env-nix.sh

# Combined test target for local + CI (unit + integration + e2e)
test: test-env-virtual test-unit test-integration test-e2e

delete-volumes: 
	@docker volume rm "pkgmgr_nix_store_${PKGMGR_DISTRO}" "pkgmgr_nix_cache_${PKGMGR_DISTRO}" || echo "No volumes to delete."

purge: delete-volumes build-no-cache

# ------------------------------------------------------------
# Uninstall target
# ------------------------------------------------------------
uninstall:
	@bash scripts/uninstall.sh
