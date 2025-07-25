# Package Manager🤖📦
[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub%20Sponsors-blue?logo=github)](https://github.com/sponsors/kevinveenbirkenbach)
[![Patreon](https://img.shields.io/badge/Support-Patreon-orange?logo=patreon)](https://www.patreon.com/c/kevinveenbirkenbach) 
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20Coffee-Funding-yellow?logo=buymeacoffee)](https://buymeacoffee.com/kevinveenbirkenbach) [![PayPal](https://img.shields.io/badge/Donate-PayPal-blue?logo=paypal)](https://s.veen.world/paypaldonate)
[![GitHub license](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GitHub repo size](https://img.shields.io/github/repo-size/kevinveenbirkenbach/package-manager)](https://github.com/kevinveenbirkenbach/package-manager)

*Kevins's* Package Manager is a configurable Python tool designed to manage multiple repositories via Bash. It automates common Git operations such as clone, pull, push, status, and more. Additionally, it handles the creation of executable wrappers and alias links for your repositories.

## Features 🚀

- **Installation & Setup:**  
  Create executable wrappers with auto-detected commands (e.g. `main.sh` or `main.py`).
  
- **Git Operations:**  
  Easily perform `git pull`, `push`, `status`, `commit`, `diff`, `add`, `show`, and `checkout` with extra parameters passed through.
  
- **Configuration Management:**  
  Manage repository configurations via a default file (`config/defaults.yaml`) and a user-specific file (`config/config.yaml`). Initialize, add, delete, or ignore entries using subcommands.
  
- **Path & Listing:**  
  Display repository paths or list all configured packages with their details.
  
- **Custom Aliases:**  
  Generate and manage custom aliases for easy command invocation.


## Installation ⚙️

Clone the repository and ensure your `~/.local/bin` is in your system PATH:

```bash
git clone https://github.com/kevinveenbirkenbach/package-manager.git
cd package-manager
```

Install make and pip if not installed yet:

```bash
pacman -S make python-pip
```

Then, run the following command to set up the project:

```bash
make setup
```

The `make setup` command will:
- Make `main.py` executable.
- Install required packages from `requirements.txt`.
- Execute `python main.py install` to complete the installation.

## Docker Quickstart 🐳

Alternatively to installing locally, you can use Docker: build the image with

```bash
docker build --no-cache -t pkgmgr .
```

or alternativ pull it via

```bash
docker pull kevinveenbirkenbach/pkgmgr:latest
```

and then run

```bash
docker run --rm pkgmgr --help
```

## Usage 📖

Run the script with different commands. For example:

- **Install all packages:**
  ```bash
  pkgmgr install --all
  ```
- **Pull updates for a specific repository:**
  ```bash
  pkgmgr pull pkgmgr
  ```
- **Commit changes with extra Git parameters:**
  ```bash
  pkgmgr commit pkgmgr -- -m "Your commit message"
  ```
- **List all configured packages:**
  ```bash
  pkgmgr config show
  ```
- **Manage configuration:**
  ```bash
  pkgmgr config init
  pkgmgr config add
  pkgmgr config edit
  pkgmgr config delete <identifier>
  pkgmgr config ignore <identifier> --set true
  ```

## License 📄

This project is licensed under the MIT License.

## Author 👤

Kevin Veen-Birkenbach  
[https://www.veen.world](https://www.veen.world)

---

**Repository:** [github.com/kevinveenbirkenbach/package-manager](https://github.com/kevinveenbirkenbach/package-manager)

*Created with AI 🤖 - [View conversation](https://chatgpt.com/share/67c728c4-92d0-800f-8945-003fa9bf27c6)*
