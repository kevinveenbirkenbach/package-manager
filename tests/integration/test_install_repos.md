# Integration Test: Command Resolution & Link Creation

**File:** `tests/integration/test_install_repos_integration.py`

This integration test validates the *end-to-end* behavior of the pkgmgr installation pipeline:

1. Repository selection
2. Verification
3. **Command resolution (`resolve_command_for_repo`)**
4. **Symlink creation (`create_ink`)**
5. Installer execution order and skipping rules

The test sets up **two repositories**:

| Repository    | Environment Condition           | Expected Behavior                    |
| ------------- | ------------------------------- | ------------------------------------ |
| `repo-system` | `/usr/bin/tool-system` exists   | System binary → **NO symlink**       |
| `repo-nix`    | Nix profile contains `tool-nix` | Link → `~/.nix-profile/bin/tool-nix` |

This confirms that pkgmgr respects system package managers, prefers Nix over fallback logic, and creates or skips symlinks appropriately.

---

## 🔧 **Command Selection Flowchart**

The integration test verifies that pkgmgr follows this exact decision tree:

```mermaid
flowchart TD

A[Start: install_repos()] --> B(resolve_command_for_repo)

B --> C{Explicit command in repo config?}
C -- Yes --> C1[Return explicit command]
C -- No --> D

D --> E{System binary under /usr/?}
E -- Yes --> E1[Return None → NO symlink]
E -- No --> F

F --> G{Nix profile binary exists?}
G -- Yes --> G1[Return Nix binary]
G -- No --> H

H --> I{Python/non-system PATH binary?}
I -- Yes --> I1[Return PATH binary]
I -- No --> J

J --> K{main.sh/main.py in repo?}
K -- Yes --> K1[Return fallback script]
K -- No --> L[Error: No command found]

L --> X[Abort installation of this repo]

C1 --> M[create_ink → create symlink]
G1 --> M
I1 --> M
K1 --> M

E1 --> N[Skip symlink creation]
```

The integration test specifically checks branches:

* **System binary → skip**
* **Nix binary → create link**

---

## 📐 **Behavior Matrix (Simplified Priority Model)**

| Priority | Layer / Condition                     | Action      | Link Created? |
| -------- | ------------------------------------- | ----------- | ------------- |
| 1        | Explicit `command` in repo config     | Use it      | ✅ Yes         |
| 2        | System binary under `/usr/bin/...`    | Respect OS  | ❌ No          |
| 3        | Nix profile binary exists             | Use it      | ✅ Yes         |
| 4        | Non-system PATH binary                | Use it      | ✅ Yes         |
| 5        | Repo fallback (`main.sh` / `main.py`) | Use it      | ✅ Yes         |
| 6        | None of the above                     | Raise error | ❌ No          |

The integration test hits row **2** and **3**.

---

## 🧪 What This Integration Test Ensures

### ✔ Correct orchestration

`install_repos()` calls components in the correct sequence and respects outputs from each stage.

### ✔ Correct command resolution

The test asserts that:

* System binaries suppress symlink creation.
* Nix binaries produce symlinks even if PATH is empty.

### ✔ Correct linking behavior

For the Nix repo:

* A symlink is created under the `bin_dir`.
* The symlink points exactly to `~/.nix-profile/bin/<identifier>`.

### ✔ Isolation

No real system binaries or actual Nix installation are required—the test uses deterministic patches.

---

## 🧩 Additional Notes

* The integration test covers only the *positive Nix case* and the *system binary skip case*.
  More tests can be added later for:

  * Python binary resolution
  * Fallback to `main.py`
  * Error case when no command can be resolved
* The test intentionally uses a **temporary HOME directory** to simulate isolated Nix profiles.

---

## ✅ Summary

This integration test validates that:

* **pkgmgr does not overwrite or override system binaries**
* **Nix takes precedence over PATH-based tools**
* **The symlink layer works correctly**
* **The installer pipeline continues normally even when command resolution skips symlink creation**

The file provides a reliable foundation for confirming that command resolution, linking, and installation orchestration are functioning exactly as designed.
