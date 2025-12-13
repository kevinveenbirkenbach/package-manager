# Nix Bootstrap (package-manager)

This directory contains the **Nix initialization and bootstrap logic** used by *package-manager* to ensure the `nix` command is available on supported systems (host machines and CI containers).

It is invoked during package installation (Arch/Debian/Fedora scriptlets) and can also be called manually.

---

## Entry Point

- *scripts/nix/init.sh*  
  Main bootstrap script. It:
  - checks whether `nix` is already available
  - adjusts `PATH` for common Nix locations
  - installs Nix when missing (daemon install on systemd hosts, single-user in containers)
  - ensures predictable `nix` availability via symlinks (without overwriting distro-managed paths)
  - validates that `nix` is usable at the end (CI-safe)

---

## Library Layout

The entry point sources small, focused modules from *scripts/nix/lib/*:

- *bootstrap_config.sh* — configuration defaults (installer URL, retry timing)
- *detect.sh* — container detection helpers
- *path.sh* — PATH adjustments and `nix` binary resolution helpers
- *symlinks.sh* — user/global symlink helpers for stable `nix` discovery
- *users.sh* — build group/users and container ownership/perms helpers
- *install.sh* — installer download + retry logic and execution helpers

Each library file includes a simple guard to prevent double-sourcing.

---

## When It Runs

This bootstrap is typically executed automatically:

- Arch: post-install / post-upgrade hook
- Debian: `postinst`
- Fedora/RPM: `%post`


---

## Notes / Design Goals

- **Cross-distro compatibility:** supports common Linux layouts (including Arch placing `nix` in */usr/sbin*).
- **Non-destructive behavior:** avoids overwriting distro-managed `nix` binaries.
- **CI robustness:** retry logic for downloads and a final `nix` availability check.
- **Container-safe defaults:** single-user install as a dedicated `nix` user when running as root in containers.

