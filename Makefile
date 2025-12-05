.PHONY: install setup uninstall aur_builder_setup test

# Local Nix cache directories in the repo
NIX_STORE_DIR := .nix/store
NIX_CACHE_DIR := .nix/cache

setup: install
	@echo "Running pkgmgr setup via main.py..."
	@if [ -x "$$HOME/.venvs/pkgmgr/bin/python" ]; then \
		echo "Using virtualenv Python at $$HOME/.venvs/pkgmgr/bin/python"; \
		"$$HOME/.venvs/pkgmgr/bin/python" main.py install; \
	else \
		echo "Virtualenv not found, falling back to system python3"; \
		python3 main.py install; \
	fi

test:
	@echo "Ensuring local Nix cache directories exist..."
	@mkdir -p "$(NIX_STORE_DIR)" "$(NIX_CACHE_DIR)"
	@echo "Building test image 'package-manager-test'..."
	docker build -t package-manager-test .
	@echo "Running tests inside Nix devShell with local cache..."
	docker run --rm \
		-v "$$(pwd)/$(NIX_STORE_DIR):/nix" \
		-v "$$(pwd)/$(NIX_CACHE_DIR):/root/.cache/nix" \
		--workdir /src \
		--entrypoint nix \
		package-manager-test \
		develop .#default --no-write-lock-file -c \
			python -m unittest discover -s tests -p "test_*.py"

install:
	@echo "Making 'main.py' executable..."
	@chmod +x main.py
	@echo "Checking if global user virtual environment exists..."
	@mkdir -p "$$HOME/.venvs"
	@if [ ! -d "$$HOME/.venvs/pkgmgr" ]; then \
		echo "Creating global venv at $$HOME/.venvs/pkgmgr..."; \
		python3 -m venv "$$HOME/.venvs/pkgmgr"; \
	fi
	@echo "Installing required Python packages into $$HOME/.venvs/pkgmgr..."
	@$$HOME/.venvs/pkgmgr/bin/python -m ensurepip --upgrade
	@$$HOME/.venvs/pkgmgr/bin/pip install --upgrade pip setuptools wheel
	@$$HOME/.venvs/pkgmgr/bin/pip install -r requirements.txt
	@echo "Ensuring $$HOME/.bashrc and $$HOME/.zshrc exist..."
	@touch "$$HOME/.bashrc" "$$HOME/.zshrc"
	@echo "Ensuring automatic activation of $$HOME/.venvs/pkgmgr for this user..."
	@for rc in "$$HOME/.bashrc" "$$HOME/.zshrc"; do \
		rc_line='if [ -d "$${HOME}/.venvs/pkgmgr" ]; then . "$${HOME}/.venvs/pkgmgr/bin/activate"; if [ -n "$${PS1:-}" ]; then echo "Global Python virtual environment '\''~/.venvs/pkgmgr'\'' activated."; fi; fi'; \
		grep -qxF "$${rc_line}" "$$rc" || echo "$${rc_line}" >> "$$rc"; \
	done
	@echo "Arch/Manjaro detection and optional AUR setup..."
	@if command -v pacman >/dev/null 2>&1; then \
		$(MAKE) aur_builder_setup; \
	else \
		echo "Not Arch-based (no pacman). Skipping aur_builder/yay setup."; \
	fi
	@echo "Installation complete. Please restart your shell (or 'exec bash' or 'exec zsh') for the changes to take effect."

# Only runs on Arch/Manjaro
aur_builder_setup:
	@echo "Setting up aur_builder and yay (Arch/Manjaro)..."
	@sudo pacman -Syu --noconfirm
	@sudo pacman -S --needed --noconfirm base-devel git sudo
	@# group & user
	@if ! getent group aur_builder >/dev/null; then sudo groupadd -r aur_builder; fi
	@if ! id -u aur_builder >/dev/null 2>&1; then sudo useradd -m -r -g aur_builder -s /bin/bash aur_builder; fi
	@# sudoers rule for pacman
	@echo '%aur_builder ALL=(ALL) NOPASSWD: /usr/bin/pacman' | sudo tee /etc/sudoers.d/aur_builder >/dev/null
	@sudo chmod 0440 /etc/sudoers.d/aur_builder
	@# yay install (if missing)
	@if ! sudo -u aur_builder bash -lc 'command -v yay >/dev/null'; then \
		sudo -u aur_builder bash -lc 'cd ~ && rm -rf yay && git clone https://aur.archlinux.org/yay.git && cd yay && makepkg -si --noconfirm'; \
	else \
		echo "yay already installed."; \
	fi
	@echo "aur_builder/yay setup complete."

uninstall:
	@echo "Removing global user virtual environment if it exists..."
	@rm -rf "$$HOME/.venvs/pkgmgr"
	@echo "Cleaning up $$HOME/.bashrc and $$HOME/.zshrc entries..."
	@for rc in "$$HOME/.bashrc" "$$HOME/.zshrc"; do \
		sed -i '/\.venvs\/pkgmgr\/bin\/activate"; if \[ -n "\$${PS1:-}" \]; then echo "Global Python virtual environment '\''~\/\.venvs\/pkgmgr'\'' activated."; fi; fi/d' "$$rc"; \
	done
	@echo "Uninstallation complete. Please restart your shell (or 'exec bash' or 'exec zsh') for the changes to fully apply."
