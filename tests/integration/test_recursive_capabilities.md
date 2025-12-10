# Capability Resolution & Installer Shadowing

This document explains how `pkgmgr` decides **which installer should run** when multiple installation mechanisms are available in a repository.
It reflects the logic shown in the setup-controller diagram:

➡️ **Full graphical schema:** [https://s.veen.world/pkgmgrmp](https://s.veen.world/pkgmgrmp)

---

## Layer Hierarchy (Strength Order)

Installers are evaluated from **strongest to weakest**.
A stronger layer shadows all layers below it.

```
┌───────────────────────────┐  Highest layer
│      OS-PACKAGES          │  (PKGBUILD / debian / rpm)
└───────────▲───────────────┘
            │ shadows lower layers
┌───────────┴───────────────┐
│           NIX              │  (flake.nix)
└───────────▲───────────────┘
            │ shadows lower layers
┌───────────┴───────────────┐
│          PYTHON            │  (pyproject.toml)
└───────────▲───────────────┘
            │ shadows lower layers
┌───────────┴───────────────┐
│         MAKEFILE           │  (Makefile)
└────────────────────────────┘  Lowest layer
```

---

## Capability Matrix

Each layer provides a set of **capabilities**.
Layers that provide *all* capabilities of a lower layer **shadow** that layer.

| Capability           | Makefile | Python       | Nix | OS-Pkgs |
| -------------------- | -------- | ------------ | --- | ------- |
| `make-install`       | ✔        | (optional) ✔ | ✔   | ✔       |
| `python-runtime`     | –        | ✔            | ✔   | ✔       |
| `binary/cli`         | –        | –            | ✔   | ✔       |
| `system-integration` | –        | –            | –   | ✔       |

✔ = capability available
– = not provided by this layer

---

## Scenario Matrix (Expected Installer Execution)

| Scenario                   | Makefile | Python | Nix | OS-Pkgs | Test Name                     |
| -------------------------- | -------- | ------ | --- | ------- | ----------------------------- |
| 1) Only Makefile           | ✔        | –      | –   | –       | `only_makefile`               |
| 2) Python + Makefile       | ✔        | ✔      | –   | –       | `python_and_makefile`         |
| 3) Python shadows Makefile | ✗        | ✔      | –   | –       | `python_shadows_makefile`     |
| 4) Nix shadows Py & MF     | ✗        | ✗      | ✔   | –       | `nix_shadows_python_makefile` |
| 5) OS-Pkgs shadow all      | ✗        | ✗      | ✗   | ✔       | `os_packages_shadow_all`      |

Legend:
✔ = installer runs
✗ = installer is skipped (shadowed)
– = layer not present in this scenario

---

## What the Integration Test Confirms

The integration tests ensure that the **actual execution** matches the theoretical capability model.

### 1) Only Makefile

* Only `Makefile` present
  → MakefileInstaller runs.

### 2) Python + Makefile

* Python provides `python-runtime`
* Makefile provides `make-install`
  → Both run (capabilities are disjoint).

### 3) Python shadows Makefile

* Python additionally advertises `make-install`
  → MakefileInstaller is skipped.

### 4) Nix shadows Python & Makefile

* Nix provides: `python-runtime` + `make-install`
  → PythonInstaller and MakefileInstaller are skipped.
  → Only NixInstaller runs.

### 5) OS-Pkg layer shadows all

* OS packages provide all capabilities
  → Only OS installer runs.

---

## Capability Processing Flowchart

```
                ┌────────────────────────────┐
                │           Start             │
                └───────────────┬────────────┘
                                │
                  provided_capabilities = ∅
                                │
                                ▼
          ┌──────────────────────────────────────────────┐
          │  For each installer in layer order (low→high) │
          └───────────────────┬──────────────────────────┘
                              │
                supports(ctx)?│
                    ┌─────────┴──────────┐
                    │        no          │
                    │   → skip installer │
                    └─────────┬──────────┘
                              │ yes
                              ▼
                 caps = detect_capabilities(layer)
                              │
         caps ⊆ provided_capabilities ?
                ┌─────────────┬─────────────┐
                │ yes         │ no           │
                │ skip        │ run installer│
                └─────────────┴──────────────┘
                                              │
                                              ▼
                           provided_capabilities ∪= caps
                                              │
                                              ▼
                             ┌────────────────────────┐
                             │ End of installer list  │
                             └────────────────────────┘
```

---

## Core Principle

**A layer is executed only if it contributes at least one capability that no stronger layer has already provided.**

---

## Link to the Setup Controller Diagram

The full visual schema is available here:

➡️ **[https://s.veen.world/pkgmgrmp](https://s.veen.world/pkgmgrmp)**
