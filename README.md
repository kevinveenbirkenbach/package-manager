# Package Manager 🤖📦

[![GitHub license](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GitHub repo size](https://img.shields.io/github/repo-size/kevinveenbirkenbach/package-manager)](https://github.com/kevinveenbirkenbach/package-manager)

Package Manager is a configurable Python tool designed to manage multiple repositories via Bash. It automates common Git operations such as clone, pull, push, status, and more. Additionally, it handles the creation of executable wrappers and alias links for your repositories.

## Features 🚀

- **Installation & Setup:**  
  Create executable wrappers with auto-detected commands (e.g. `main.sh` or `main.py`) and optional setup/teardown commands.
  
- **Git Operations:**  
  Easily perform `git pull`, `push`, `status`, `commit`, `diff`, `add`, `show`, and `checkout` with extra parameters passed through.
  
- **Configuration Management:**  
  Manage repository configurations via a default file (`config/defaults.yaml`) and a user-specific file (`config/config.yaml`). Initialize, add, delete, or ignore entries using subcommands.
  
- **Path & Listing:**  
  Display repository paths or list all configured packages with their details.
  
- **Custom Aliases:**  
  Generate and manage custom aliases for easy command invocation.

## Installation ⚙️

Clone the repository and make sure your `~/.local/bin` is in your system PATH:

```bash
git clone https://github.com/kevinveenbirkenbach/package-manager.git
cd package-manager
chmod +x main.py
```

Then install or update your commands:

```bash
./main.py install --all
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
