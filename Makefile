.PHONY: install setup uninstall aur_builder_setup

setup: install
	@python3 main.py install

install:
	@echo "Making 'main.py' executable..."
	@chmod +x main.py
	@echo "Checking if global user virtual environment exists..."
	@mkdir -p ~/.venvs
	@if [ ! -d ~/.venvs/pkgmgr ]; then \
		echo "Creating global venv at ~/.venvs/pkgmgr..."; \
		python3 -m venv ~/.venvs/pkgmgr; \
	fi
	@echo "Installing required Python packages into ~/.venvs/pkgmgr..."
	@~/.venvs/pkgmgr/bin/python -m ensurepip --upgrade
	@~/.venvs/pkgmgr/bin/pip install --upgrade pip setuptools wheel
	@~/.venvs/pkgmgr/bin/pip install -r requirements.txt
	@echo "Ensuring ~/.bashrc and ~/.zshrc exist..."
	@touch ~/.bashrc ~/.zshrc
	@echo "Ensuring automatic activation of ~/.venvs/pkgmgr for this user..."
	@for rc in ~/.bashrc ~/.zshrc; do \
		rc_line='if [ -d "$${HOME}/.venvs/pkgmgr" ]; then . "$${HOME}/.venvs/pkgmgr/bin/activate"; echo "Global Python virtual environment '\''~/.venvs/pkgmgr'\'' activated."; fi'; \
		grep -qxF "$${rc_line}" $$rc || echo "$${rc_line}" >> $$rc; \
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
	@rm -rf ~/.venvs/pkgmgr
	@echo "Cleaning up ~/.bashrc and ~/.zshrc entries..."
	@for rc in ~/.bashrc ~/.zshrc; do \
		sed -i '/\.venvs\/pkgmgr\/bin\/activate"; echo "Global Python virtual environment '\''~\/\.venvs\/pkgmgr'\'' activated."; fi/d' $$rc; \
	done
	@echo "Uninstallation complete. Please restart your shell (or 'exec bash' or 'exec zsh') for the changes to fully apply."
