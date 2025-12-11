.PHONY: install setup uninstall \
        test build build-no-cache test-unit test-e2e test-integration \
        test-container

# Distro
# Options: arch debian ubuntu fedora centos
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

# ------------------------------------------------------------
# PKGMGR setup (developer wrapper -> scripts/installation/main.sh)
# ------------------------------------------------------------
setup:
	@bash scripts/installation/main.sh

# ------------------------------------------------------------
# Docker build targets (delegated to scripts/build)
# ------------------------------------------------------------
build-no-cache:
	@bash scripts/build/build-image-no-cache.sh

build:
	@bash scripts/build/build-image.sh

# ------------------------------------------------------------
# Test targets (delegated to scripts/test)
# ------------------------------------------------------------

test-unit: build-missing
	@bash scripts/test/test-unit.sh

test-integration: build-missing
	@bash scripts/test/test-integration.sh

test-e2e: build-missing
	@bash scripts/test/test-e2e.sh

test-container: build-missing
	@bash scripts/test/test-container.sh

# ------------------------------------------------------------
# Build only missing container images
# ------------------------------------------------------------
build-missing:
	@bash scripts/build/build-image-missing.sh

# Combined test target for local + CI (unit + integration + e2e)
test: test-container test-unit test-integration test-e2e

# ------------------------------------------------------------
# System install (native packages, calls scripts/installation/run-package.sh)
# ------------------------------------------------------------
install:
	@echo "Building and installing distro-native package-manager for this system..."
	@bash scripts/installation/run-package.sh

# ------------------------------------------------------------
# Uninstall target
# ------------------------------------------------------------
uninstall:
	@bash scripts/uninstall.sh
