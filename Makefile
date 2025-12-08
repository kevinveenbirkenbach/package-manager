.PHONY: install setup uninstall aur_builder_setup \
        test build build-no-cache test-unit test-e2e test-integration

# ------------------------------------------------------------
# Local Nix cache directories in the repo
# ------------------------------------------------------------
NIX_STORE_VOLUME := pkgmgr_nix_store
NIX_CACHE_VOLUME := pkgmgr_nix_cache

# ------------------------------------------------------------
# Distro list and base images
# ------------------------------------------------------------
DISTROS := arch debian ubuntu fedora centos

BASE_IMAGE_arch   := archlinux:latest
BASE_IMAGE_debian := debian:stable-slim
BASE_IMAGE_ubuntu := ubuntu:latest
BASE_IMAGE_fedora := fedora:latest
BASE_IMAGE_centos := quay.io/centos/centos:stream9

# Helper to echo which image is used for which distro (purely informational)
define echo_build_info
	@echo "Building image for distro '$(1)' with base image '$(2)'..."
endef

# ------------------------------------------------------------
# PKGMGR setup (wrapper)
# ------------------------------------------------------------
setup: install
	@echo "Running pkgmgr setup via main.py..."
	@if [ -x "$$HOME/.venvs/pkgmgr/bin/python" ]; then \
		echo "Using virtualenv Python at $$HOME/.venvs/pkgmgr/bin/python"; \
		"$$HOME/.venvs/pkgmgr/bin/python" main.py install; \
	else \
		echo "Virtualenv not found, falling back to system python3"; \
		python3 main.py install; \
	fi

# ------------------------------------------------------------
# Docker build targets: build all images
# ------------------------------------------------------------
build-no-cache:
	@for distro in $(DISTROS); do \
		case "$$distro" in \
			arch)   base_image="$(BASE_IMAGE_arch)" ;; \
			debian) base_image="$(BASE_IMAGE_debian)" ;; \
			ubuntu) base_image="$(BASE_IMAGE_ubuntu)" ;; \
			fedora) base_image="$(BASE_IMAGE_fedora)" ;; \
			centos) base_image="$(BASE_IMAGE_centos)" ;; \
			*)      echo "Unknown distro '$$distro'" >&2; exit 1 ;; \
		esac; \
		echo "Building test image 'package-manager-test-$$distro' with no cache (BASE_IMAGE=$$base_image)..."; \
		docker build --no-cache \
			--build-arg BASE_IMAGE="$$base_image" \
			-t "package-manager-test-$$distro" . || exit $$?; \
	done

build:
	@for distro in $(DISTROS); do \
		case "$$distro" in \
			arch)   base_image="$(BASE_IMAGE_arch)" ;; \
			debian) base_image="$(BASE_IMAGE_debian)" ;; \
			ubuntu) base_image="$(BASE_IMAGE_ubuntu)" ;; \
			fedora) base_image="$(BASE_IMAGE_fedora)" ;; \
			centos) base_image="$(BASE_IMAGE_centos)" ;; \
			*)      echo "Unknown distro '$$distro'" >&2; exit 1 ;; \
		esac; \
		echo "Building test image 'package-manager-test-$$distro' (BASE_IMAGE=$$base_image)..."; \
		docker build \
			--build-arg BASE_IMAGE="$$base_image" \
			-t "package-manager-test-$$distro" . || exit $$?; \
	done

build-arch:
	@base_image="$(BASE_IMAGE_arch)"; \
	echo "Building test image 'package-manager-test-arch' (BASE_IMAGE=$$base_image)..."; \
	docker build \
		--build-arg BASE_IMAGE="$$base_image" \
		-t "package-manager-test-arch" . || exit $$?;

# ------------------------------------------------------------
# Test targets
# ------------------------------------------------------------

# Unit tests: only in Arch container (fastest feedback)
test-unit: build-arch
	@echo "============================================================"
	@echo ">>> Running UNIT tests in Arch container"
	@echo "============================================================"
	docker run --rm \
		-v "$$(pwd):/src" \
		--workdir /src \
		--entrypoint bash \
		"package-manager-test-arch" \
		-c '\
			set -e; \
			if [ -f /etc/os-release ]; then . /etc/os-release; fi; \
			echo "Detected container distro: $${ID:-unknown} (like: $${ID_LIKE:-})"; \
			echo "Running Python unit tests (tests/unit)..."; \
			git config --global --add safe.directory /src || true; \
			cd /src; \
			export PYTHONPATH=/src:$${PYTHONPATH}; \
			python -m unittest discover \
				-s tests/unit \
				-t /src \
				-p "test_*.py"; \
		'

# Integration tests: also in Arch container, but using tests/integration
test-integration: build
	@echo "============================================================"
	@echo ">>> Running INTEGRATION tests in Arch container"
	@echo "============================================================"
	docker run --rm \
		-v "$$(pwd):/src" \
		--workdir /src \
		--entrypoint bash \
		"package-manager-test-arch" \
		-c '\
			set -e; \
			if [ -f /etc/os-release ]; then . /etc/os-release; fi; \
			echo "Detected container distro: $${ID:-unknown} (like: $${ID_LIKE:-})"; \
			echo "Running Python integration tests (tests/integration)..."; \
			git config --global --add safe.directory /src || true; \
			cd /src; \
			export PYTHONPATH=/src:$${PYTHONPATH}; \
			python -m unittest discover \
				-s tests/integration \
				-t /src \
				-p "test_*.py"; \
		'

# End-to-end tests: run in all distros via Nix devShell (tests/e2e)
test-e2e: build
	@echo "Ensuring Docker Nix volumes exist (auto-created if missing)..."
	@echo "Running E2E tests inside Nix devShell with cached store for all distros: $(DISTROS)"

	@for distro in $(DISTROS); do \
		echo "============================================================"; \
		echo ">>> Running E2E tests in container for distro: $$distro"; \
		echo "============================================================"; \
		# Only for Arch: mount /nix as volume, for others use image-installed Nix \
		if [ "$$distro" = "arch" ]; then \
			NIX_STORE_MOUNT="-v $(NIX_STORE_VOLUME):/nix"; \
		else \
			NIX_STORE_MOUNT=""; \
		fi; \
		docker run --rm \
			-v "$$(pwd):/src" \
			$$NIX_STORE_MOUNT \
			-v "$(NIX_CACHE_VOLUME):/root/.cache/nix" \
			--workdir /src \
			--entrypoint bash \
			"package-manager-test-$$distro" \
			-c '\
				set -e; \
				if [ -f /etc/os-release ]; then . /etc/os-release; fi; \
				echo "Detected container distro: $${ID:-unknown} (like: $${ID_LIKE:-})"; \
				echo "Preparing Nix environment..."; \
				if [ -f "/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh" ]; then \
					. "/nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh"; \
				fi; \
				if [ -f "$$HOME/.nix-profile/etc/profile.d/nix.sh" ]; then \
					. "$$HOME/.nix-profile/etc/profile.d/nix.sh"; \
				fi; \
				PATH="/nix/var/nix/profiles/default/bin:$$HOME/.nix-profile/bin:$$PATH"; \
				export PATH; \
				echo "PATH is now:"; \
				echo "$$PATH"; \
				NIX_CMD=""; \
				if command -v nix >/dev/null 2>&1; then \
					echo "Found nix on PATH:"; \
					command -v nix; \
					NIX_CMD="nix"; \
				else \
					echo "nix not found on PATH, scanning /nix/store for a nix binary..."; \
					for path in /nix/store/*-nix-*/bin/nix; do \
						if [ -x "$$path" ]; then \
							echo "Found nix binary at $$path"; \
							NIX_CMD="$$path"; \
							break; \
						fi; \
					done; \
				fi; \
				if [ -z "$$NIX_CMD" ]; then \
					echo "ERROR: nix binary not found anywhere – cannot run devShell"; \
					exit 1; \
				fi; \
				echo "Using Nix command: $$NIX_CMD"; \
				echo "Run E2E tests inside Nix devShell (tests/e2e)..."; \
				git config --global --add safe.directory /src || true; \
				cd /src; \
				"$$NIX_CMD" develop .#default --no-write-lock-file -c \
					python3 -m unittest discover \
						-s /src/tests/e2e \
						-p "test_*.py"; \
			' || exit $$?; \
	done

# Combined test target for local + CI (unit + e2e + integration)
test: build test-unit test-e2e test-integration

# ------------------------------------------------------------
# Installer for host systems (original logic)
# ------------------------------------------------------------
install:
	@if [ -n "$$IN_NIX_SHELL" ]; then \
		echo "Nix shell detected (IN_NIX_SHELL=1). Skipping venv/pip install – handled by Nix flake."; \
	else \
		echo "Making 'main.py' executable..."; \
		chmod +x main.py; \
		echo "Checking if global user virtual environment exists..."; \
		mkdir -p "$$HOME/.venvs"; \
		if [ ! -d "$$HOME/.venvs/pkgmgr" ]; then \
			echo "Creating global venv at $$HOME/.venvs/pkgmgr..."; \
			python3 -m venv "$$HOME/.venvs/pkgmgr"; \
		fi; \
		echo "Installing required Python packages into $$HOME/.venvs/pkgmgr..."; \
		"$$HOME/.venvs/pkgmgr/bin/python" -m ensurepip --upgrade; \
		"$$HOME/.venvs/pkgmgr/bin/pip" install --upgrade pip setuptools wheel; \
		echo "Looking for requirements.txt / _requirements.txt..."; \
		if [ -f requirements.txt ]; then \
			echo "Installing Python packages from requirements.txt..."; \
			"$$HOME/.venvs/pkgmgr/bin/pip" install -r requirements.txt; \
		elif [ -f _requirements.txt ]; then \
			echo "Installing Python packages from _requirements.txt..."; \
			"$$HOME/.venvs/pkgmgr/bin/pip" install -r _requirements.txt; \
		else \
			echo "No requirements.txt or _requirements.txt found, skipping dependency installation."; \
		fi; \
		echo "Ensuring $$HOME/.bashrc and $$HOME/.zshrc exist..."; \
		touch "$$HOME/.bashrc" "$$HOME/.zshrc"; \
		echo "Ensuring automatic activation of $$HOME/.venvs/pkgmgr for this user..."; \
		for rc in "$$HOME/.bashrc" "$$HOME/.zshrc"; do \
			rc_line='if [ -d "$${HOME}/.venvs/pkgmgr" ]; then . "$${HOME}/.venvs/pkgmgr/bin/activate"; if [ -n "$${PS1:-}" ]; then echo "Global Python virtual environment '\''~/.venvs/pkgmgr'\'' activated."; fi; fi'; \
			grep -qxF "$${rc_line}" "$$rc" || echo "$${rc_line}" >> "$$rc"; \
		done; \
		echo "Arch/Manjaro detection and optional AUR setup..."; \
		if command -v pacman >/dev/null 2>&1; then \
			$(MAKE) aur_builder_setup; \
		else \
			echo "Not Arch-based (no pacman). Skipping aur_builder/yay setup."; \
		fi; \
		echo "Installation complete. Please restart your shell (or 'exec bash' or 'exec zsh') for the changes to take effect."; \
	fi

# ------------------------------------------------------------
# AUR builder setup — only on Arch/Manjaro
# ------------------------------------------------------------
aur_builder_setup:
	@echo "Setting up aur_builder and yay (Arch/Manjaro)..."
	@sudo pacman -Syu --noconfirm
	@sudo pacman -S --needed --noconfirm base-devel git sudo
	@if ! getent group aur_builder >/dev/null; then sudo groupadd -r aur_builder; fi
	@if ! id -u aur_builder >/dev/null 2>&1; then sudo useradd -m -r -g aur_builder -s /bin/bash aur_builder; fi
	@echo '%aur_builder ALL=(ALL) NOPASSWD: /usr/bin/pacman' | sudo tee /etc/sudoers.d/aur_builder >/dev/null
	@sudo chmod 0440 /etc/sudoers.d/aur_builder
	@if ! sudo -u aur_builder bash -lc 'command -v yay >/dev/null'; then \
		sudo -u aur_builder bash -lc 'cd ~ && rm -rf yay && git clone https://aur.archlinux.org/yay.git && cd yay && makepkg -si --noconfirm'; \
	else \
		echo "yay already installed."; \
	fi
	@echo "aur_builder/yay setup complete."

# ------------------------------------------------------------
# Uninstall target
# ------------------------------------------------------------
uninstall:
	@echo "Removing global user virtual environment if it exists..."
	@rm -rf "$$HOME/.venvs/pkgmgr"
	@echo "Cleaning up $$HOME/.bashrc and $$HOME/.zshrc entries..."
	@for rc in "$$HOME/.bashrc" "$$HOME/.zshrc"; do \
		sed -i '/\.venvs\/pkgmgr\/bin\/activate"; if \[ -n "\$${PS1:-}" \]; then echo "Global Python virtual environment '\''~\/\.venvs\/pkgmgr'\'' activated."; fi; fi/d' "$$rc"; \
	done
	@echo "Uninstallation complete. Please restart your shell (or 'exec bash' or 'exec zsh') for the changes to fully apply."
