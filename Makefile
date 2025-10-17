.PHONY: install setup uninstall

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
	@echo "Installation complete. Please restart your shell (or 'exec bash' or 'exec zsh') for the changes to take effect."

uninstall:
	@echo "Removing global user virtual environment if it exists..."
	@rm -rf ~/.venvs/pkgmgr
	@echo "Cleaning up ~/.bashrc and ~/.zshrc entries..."
	@for rc in ~/.bashrc ~/.zshrc; do \
		sed -i '/\.venvs\/pkgmgr\/bin\/activate"; echo "Global Python virtual environment '\''~\/\.venvs\/pkgmgr'\'' activated."; fi/d' $$rc; \
	done
	@echo "Uninstallation complete. Please restart your shell (or 'exec bash' or 'exec zsh') for the changes to fully apply."
