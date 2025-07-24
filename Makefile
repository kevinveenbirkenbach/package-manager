.PHONY: install setup

setup: install
	@python main.py install

install:
	@echo "Making 'main.py' executable..."
	@chmod +x main.py
	@echo "Checking if global user virtual environment exists..."
	@test -d ~/.venvs/pkgmgr || (echo "Creating global venv at ~/.venvs/pkgmgr..." && python -m venv ~/.venvs/pkgmgr)
	@echo "Installing required Python packages into ~/.venvs/pkgmgr..."
	@~/.venvs/pkgmgr/bin/pip install --upgrade pip
	@~/.venvs/pkgmgr/bin/pip install -r requirements.txt
	@echo "Ensuring ~/.bashrc exists..."
	@test -f ~/.bashrc || touch ~/.bashrc
	@echo "Ensuring automatic activation of ~/.venvs/pkgmgr for this user..."
	@grep -qxF 'if [ -d "$$HOME/.venvs/pkgmgr" ]; then . "$$HOME/.venvs/pkgmgr/bin/activate"; echo "Global Python virtual environment '\''~/.venvs/pkgmgr'\'' activated."; fi' ~/.bashrc \
		|| echo 'if [ -d "$$HOME/.venvs/pkgmgr" ]; then . "$$HOME/.venvs/pkgmgr/bin/activate"; echo "Global Python virtual environment '\''~/.venvs/pkgmgr'\'' activated."; fi' >> ~/.bashrc
	@echo "Installation complete. Please restart your shell (or 'exec bash') for the changes to take effect."

uninstall:
	@echo "Removing global user virtual environment if it exists..."
	@rm -rf ~/.venvs/pkgmgr
	@echo "Cleaning up ~/.bashrc entries..."
	@sed -i '/if \[ -d "\$\$HOME\/\.venvs\/pkgmgr" \]; then \. "\$\$HOME\/\.venvs\/pkgmgr\/bin\/activate"; echo "Global Python virtual environment '\\''~\/.venvs\/pkgmgr'\\'' activated."; fi/d' ~/.bashrc
	@echo "Uninstallation complete. Please restart your shell (or 'exec bash') for the changes to fully apply."

