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
	@grep -qxF 'if [ -d "$$HOME/.venvs/pkgmgr" ]; then export VIRTUAL_ENV="$$HOME/.venvs/pkgmgr"; export PATH="$$VIRTUAL_ENV/bin:$$PATH"; unset PYTHONHOME; fi' ~/.bashrc \
		|| echo 'if [ -d "$$HOME/.venvs/pkgmgr" ]; then export VIRTUAL_ENV="$$HOME/.venvs/pkgmgr"; export PATH="$$VIRTUAL_ENV/bin:$$PATH"; unset PYTHONHOME; fi' >> ~/.bashrc
	@grep -qxF 'echo "Global Python virtual environment '\''~/.venvs/pkgmgr'\'' activated."' ~/.bashrc \
		|| echo 'echo "Global Python virtual environment '\''~/.venvs/pkgmgr'\'' activated."' >> ~/.bashrc
	@echo "Installation complete. Please restart your shell (or 'exec bash') for the changes to take effect."

uninstall:
	@echo "Removing global user virtual environment if it exists..."
	@rm -rf ~/.venvs/pkgmgr
	@echo "Cleaning up ~/.bashrc entries..."
	@sed -i '/Global Python virtual environment '\''~\/.venvs\/pkgmgr'\'' activated\./d' ~/.bashrc
	@sed -i '/if \[ -d "\$\$HOME\/\.venvs\/pkgmgr" \]; then export VIRTUAL_ENV="\$\$HOME\/\.venvs\/pkgmgr"; export PATH="\$\$VIRTUAL_ENV\/bin:\$\$PATH"; unset PYTHONHOME; fi/d' ~/.bashrc
	@echo "Uninstallation complete. Please restart your shell (or 'exec bash') for the changes to fully apply."

