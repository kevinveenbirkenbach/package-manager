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
development lifecycle**. It provides one configuration for all repositories,
one unified CLI to interact with them, and a Nix-based foundation that keeps
tooling reproducible across distributions.

Native package managers are still used where they make sense. PKGMGR coordinates
the surrounding development, build and release workflows in a consistent way.

In addition, PKGMGR provides Docker images that can serve as a **reproducible
system baseline**. These images bundle the complete PKGMGR toolchain and are
designed to be reused as a stable execution environment across machines,
pipelines and teams. This approach is specifically used within
[**Infinito.Nexus**](https://s.infinito.nexus/code) to make complex systems
distribution-independent while remaining fully reproducible.

---

## Features 🚀

PKGMGR enables multi-distro development and packaging by managing multiple
repositories from a single configuration file. It drives complete release
pipelines across Linux distributions using Nix flakes, Python build metadata,
native OS packages such as Arch, Debian and RPM formats, and additional ecosystem
integrations like Ansible.

All functionality is exposed through a unified `pkgmgr` command-line interface
that works identically on every supported distribution. It combines repository
management, Git operations, Docker and Compose orchestration, as well as
versioning, release and changelog workflows. Many commands support a preview
mode, allowing you to inspect the underlying actions before they are executed.

---

### Full development workflows

PKGMGR is not just a helper around Git commands. Combined with its release and
versioning features it can drive **end-to-end workflows**:

1. Clone and mirror repositories.
2. Run tests and builds through `make` or Nix.
3. Bump versions, update changelogs and tags.
4. Build distro-specific packages.
5. Keep all mirrors and working copies in sync.

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

## Installation ⚙️

PKGMGR can be installed using `make`.
The setup mode defines **which runtime layers are prepared**.
---

### Download

```bash
git clone https://github.com/kevinveenbirkenbach/package-manager.git
cd package-manager
```

### Dependency installation (optional)

System dependencies required **before running any *make* commands** are installed via:

```
scripts/installation/dependencies.sh
```

The script detects and normalizes the OS and installs the required **system-level dependencies** accordingly.

### Install

```bash
git clone https://github.com/kevinveenbirkenbach/package-manager.git
cd package-manager
make install
```

### Setup modes

| Command             | Prepares                | Use case              |
| ------------------- | ----------------------- | --------------------- |
| **make setup**      | Python venv **and** Nix | Full development & CI |
| **make setup-venv** | Python venv only        | Local user setup      |


##### Full setup (venv + Nix)

```bash
make setup
```

Use this for CI, servers, containers and full development workflows.

##### Venv-only setup

```bash
make setup-venv
source ~/.venvs/pkgmgr/bin/activate
```

Use this if you want PKGMGR isolated without Nix integration.

---

Alles klar 🙂
Hier ist der **RUN-Abschnitt ohne Gedankenstriche**, klar nach **Nix, Docker und venv** getrennt:

---

## Run PKGMGR 🧰

PKGMGR can be executed in different environments.
All modes expose the same CLI and commands.

---

### Run via Nix (no installation)

```bash
nix run github:kevinveenbirkenbach/package-manager#pkgmgr -- --help
```

---

### Run via Docker 🐳

PKGMGR can be executed **inside Docker containers** for CI, testing and isolated
workflows.
---

#### Container types

Two container types are available.


| Image type | Contains                      | Typical use             |
| ---------- | ----------------------------- | ----------------------- |
| **Virgin** | Base OS + system dependencies | Clean test environments |
| **Stable** | PKGMGR + Nix (flakes enabled) | Ready-to-use workflows  |

Example images:

* Virgin: `pkgmgr-arch-virgin`
* Stable: `ghcr.io/kevinveenbirkenbach/pkgmgr:stable`


Use **virgin images** for isolated test runs,
use the **stable image** for fast, reproducible execution.

---

#### Run examples

```bash
docker run --rm -it \
  -v "$PWD":/src \
  -w /src \
  ghcr.io/kevinveenbirkenbach/pkgmgr:stable \
  pkgmgr --help
```

---

### Run via virtual environment (venv)

After activating the venv:

```bash
pkgmgr --help
```

---

This allows you to choose between zero install execution using Nix, fully prebuilt
Docker environments or local isolated venv setups with identical command behavior.

---

## License 📄

This project is licensed under the MIT License.
See the [LICENSE](LICENSE) file for details.

---

## Author 👤

Kevin Veen-Birkenbach
[https://www.veen.world](https://www.veen.world)
