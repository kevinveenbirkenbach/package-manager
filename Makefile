.PHONY: install setup

setup: install
	@python main.py install

install:
	@echo "Making 'main.py' executable..."
	@chmod +x main.py
	@echo "Installing packages from 'requirements.txt'..."
	@pip install -r requirements.txt --break-system-packages
