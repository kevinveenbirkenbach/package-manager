# Capability Resolution & Installer Shadowing

## Layer Hierarchy

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

## Scenario Matrix

| Scenario                   | Makefile | Python | Nix | OS-Pkgs | Test Name                     |
| -------------------------- | -------- | ------ | --- | ------- | ----------------------------- |
| 1) Only Makefile           | ✔        | –      | –   | –       | `only_makefile`               |
| 2) Python + Makefile       | ✔        | ✔      | –   | –       | `python_and_makefile`         |
| 3) Python shadows Makefile | ✗        | ✔      | –   | –       | `python_shadows_makefile`     |
| 4) Nix shadows Py & MF     | ✗        | ✗      | ✔   | –       | `nix_shadows_python_makefile` |
| 5) OS-Pkgs shadow all      | ✗        | ✗      | ✗   | ✔       | `os_packages_shadow_all`      |

Legend:
✔ = installer runs
✗ = installer skipped (shadowed by upper layer)
– = no such layer present

---

## What the Integration Test Confirms

**Goal:** Validate that the capability-shadowing mechanism correctly determines *which installers actually run* for a given repository layout.

### 1) Only Makefile

* Makefile provides `make-install`.
* No higher layers → MakefileInstaller runs.

### 2) Python + Makefile

* Python provides `python-runtime`.
* Makefile additionally provides `make-install`.
* No capability overlap → both installers run.

### 3) Python shadows Makefile

* Python also provides `make-install`.
* Makefile’s capability is fully covered → MakefileInstaller is skipped.

### 4) Nix shadows Python & Makefile

* Nix provides all capabilities below it.
* Only NixInstaller runs.

### 5) OS-Packages shadow all

* PKGBUILD/debian/rpm provide all capabilities.
* Only the corresponding OS package installer runs.

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

## Core Principle (one sentence)

**A layer only executes if it provides at least one capability not already guaranteed by any higher layer.**
