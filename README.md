# Package Manager 🤖📦

![PKGMGR Banner](assets/banner.jpg)

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub%20Sponsors-blue?logo=github)](https://github.com/sponsors/kevinveenbirkenbach)
[![Patreon](https://img.shields.io/badge/Support-Patreon-orange?logo=patreon)](https://www.patreon.com/c/kevinveenbirkenbach)
[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20me%20a%20Coffee-Funding-yellow?logo=buymeacoffee)](https://buymeacoffee.com/kevinveenbirkenbach)
[![PayPal](https://img.shields.io/badge/Donate-PayPal-blue?logo=paypal)](https://s.veen.world/paypaldonate)
[![GitHub license](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![GitHub repo size](https://img.shields.io/github/repo-size/kevinveenbirkenbach/package-manager)](https://github.com/kevinveenbirkenbach/package-manager)
[![Mark stable commit](https://github.com/kevinveenbirkenbach/package-manager/actions/workflows/mark-stable.yml/badge.svg)](https://github.com/kevinveenbirkenbach/package-manager/actions/workflows/mark-stable.yml)

[**Kevin's Package Manager (PKGMGR)**](https://s.veen.world/pkgmgr) is a *multi-distro* package manager and workflow orchestrator.
It helps you **develop, package, release and manage projects across multiple Linux-based
operating systems** (Arch, Debian, Ubuntu, Fedora, CentOS, …).

PKGMGR is implemented in **Python** and uses **Nix (flakes)** as a foundation for
distribution-independent builds and tooling. On top of that it provides a rich
CLI that proxies common developer tools (Git, Docker, Make, …) and glues them
together into repeatable development workflows.

---

## Why PKGMGR? 🧠

Traditional distro package managers like `apt`, `pacman` or `dnf` focus on a
single operating system. PKGMGR instead focuses on **your repositories and
development lifecycle**:

* one configuration for all your repos,
* one CLI to interact with them,
* one Nix-based layer to keep tooling reproducible across distros.

You keep using your native package manager where it makes sense – PKGMGR
coordinates the *development and release flow* around it.

---

## Features 🚀

### Multi-distro development & packaging

* Manage **many repositories at once** from a single `config/config.yaml`.
* Drive full **release pipelines** across Linux distributions using:

  * Nix flakes (`flake.nix`)
  * PyPI style builds (`pyproject.toml`)
  * OS packages (PKGBUILD, Debian control/changelog, RPM spec)
  * Ansible Galaxy metadata and more.

### Rich CLI for daily work

All commands are exposed via the `pkgmgr` CLI and are available on every distro:

* **Repository management**

  * `clone`, `update`, `install`, `delete`, `deinstall`, `path`, `list`, `config`
* **Git proxies**

  * `pull`, `push`, `status`, `diff`, `add`, `show`, `checkout`,
    `reset`, `revert`, `rebase`, `commit`, `branch`
* **Docker & Compose orchestration**

  * `build`, `up`, `down`, `exec`, `ps`, `start`, `stop`, `restart`
* **Release toolchain**

  * `version`, `release`, `changelog`, `make`
* **Mirror & workflow helpers**

  * `mirror` (list/diff/merge/setup), `shell`, `terminal`, `code`, `explore`

Many of these commands support `--preview` mode so you can inspect the
underlying Git or Docker calls without executing them.

### Full development workflows

PKGMGR is not just a helper around Git commands. Combined with its release and
versioning features it can drive **end-to-end workflows**:

1. Clone and mirror repositories.
2. Run tests and builds through `make` or Nix.
3. Bump versions, update changelogs and tags.
4. Build distro-specific packages.
5. Keep all mirrors and working copies in sync.

The extensive E2E tests (`tests/e2e/`) and GitHub Actions workflows (including
“virgin user” and “virgin root” Arch tests) validate these flows across
different Linux environments.

---

## Architecture & Setup Map 🗺️

The following diagram gives a full overview of:

* PKGMGR’s package structure,
* the layered installers (OS, foundation, Python, Makefile),
* and the setup controller that decides which layer to use on a given system.

![PKGMGR Architecture](assets/map.png)

**Diagram status:** 12 December 2025
**Always-up-to-date version:** [https://s.veen.world/pkgmgrmp](https://s.veen.world/pkgmgrmp)

---

Perfekt, dann hier die **noch kompaktere und korrekt differenzierte Version**, die **nur** zwischen
**`make setup`** und **`make setup-venv`** unterscheidet und exakt deinem Verhalten entspricht.

README-ready, ohne Over-Engineering.

---

## Installation ⚙️

PKGMGR can be installed using `make`.
The setup mode defines **which runtime layers are prepared**.

---

### Setup modes

| Command             | Prepares                | Use case              |
| ------------------- | ----------------------- | --------------------- |
| **make setup**      | Python venv **and** Nix | Full development & CI |
| **make setup-venv** | Python venv only        | Local user setup      |

---

### Install & setup

```bash
git clone https://github.com/kevinveenbirkenbach/package-manager.git
cd package-manager
make install
```

#### Full setup (venv + Nix)

```bash
make setup
```

Use this for CI, servers, containers and full development workflows.

#### Venv-only setup

```bash
make setup-venv
source ~/.venvs/pkgmgr/bin/activate
```

Use this if you want PKGMGR isolated without Nix integration.

---

## Run without installation (Nix)

Run PKGMGR directly via Nix Flakes.

```bash
nix run github:kevinveenbirkenbach/package-manager#pkgmgr -- --help
```

Example:

```bash
nix run github:kevinveenbirkenbach/package-manager#pkgmgr -- version pkgmgr
```

Notes:

* full flake URL required
* `--` separates Nix and PKGMGR arguments
* can be used alongside any setup mode

---

## Usage 🧰

After installation, the main entry point is:

```bash
pkgmgr --help
```

This prints a list of all available subcommands.
The help for each command is available via:

---

## License 📄

This project is licensed under the MIT License.
See the [LICENSE](LICENSE) file for details.

---

## Author 👤

Kevin Veen-Birkenbach
[https://www.veen.world](https://www.veen.world)
