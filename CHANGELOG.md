## [1.4.1] - 2025-12-12

* Fixed (#1) stable release container publishing


## [1.4.0] - 2025-12-12

* **Docker Container Building**

* New official container images are automatically published on each release.
* Images are available per distribution and as a default Arch-based image.
* Stable releases now provide an additional `stable` container tag.


## [1.3.1] - 2025-12-12

* Updated documentation with better run and installation instructions


## [1.3.0] - 2025-12-12

* **Minor release – Stability & CI hardening**

* Stabilized Nix resolution and global symlink handling across Arch, CentOS, Debian, and Ubuntu
* Ensured Nix works reliably in CI, sudo, login, and non-login shells without overriding distro-managed paths
* Improved error handling and deterministic behavior for non-root environments
* Refactored Docker and CI workflows for reproducible multi-distro virgin tests
* Made E2E tests more realistic by executing real CLI commands
* Fixed Python compatibility and missing dependencies on affected distros


## [1.2.1] - 2025-12-12

* **Changed**

* Split container tests into *virtualenv* and *Nix flake* environments to clearly separate Python and Nix responsibilities.

**Fixed**

* Fixed Nix installer permission issues when running under a different user in containers.
* Improved reliability of post-install Nix initialization across all distro packages.

**CI**

* Replaced generic container tests with explicit environment checks.
* Validate Nix availability via *nix flake* tests instead of Docker build-time side effects.


## [1.2.0] - 2025-12-12

* **Release workflow overhaul**

* Introduced a fully structured release workflow with clear phases and safeguards
* Added preview-first releases with explicit confirmation before execution
* Automatic handling of *latest* tag when a release is the newest version
* Optional branch closing after successful releases with interactive confirmation
* Improved safety by syncing with remote before any changes
* Clear separation of concerns (workflow, git handling, prompts, versioning)


## [1.1.0] - 2025-12-12

* Added *branch drop* for destructive branch deletion and introduced *--force/-f* flags for branch close and branch drop to skip confirmation prompts.


## [1.0.0] - 2025-12-11

* **1.0.0 – Official Stable Release 🎉**
*First stable release of PKGMGR, the multi-distro development and package workflow manager.*

---

**Key Features**

**Core Functionality**

* Manage many repositories with one CLI: `clone`, `update`, `install`, `list`, `path`, `config`
* Proxy wrappers for Git, Docker/Compose and Make
* Multi-repo execution with safe *preview mode*
* Mirror management: `mirror list/diff/merge/setup`

**Releases & Versioning**

* Automated SemVer bumps, tagging and changelog generation
* Supports PKGBUILD, Debian, RPM, pyproject.toml, flake.nix

**Developer Tools**

* Open repositories in VS Code, file manager or terminal
* Unified workflows across all major Linux distros

**Nix Integration**

* Cross-distro reproducible builds via Nix flakes
* CI-tested across all supported environments

---

**Summary**
PKGMGR 1.0.0 unifies repository management, build tooling, release automation and reproducible multi-distro workflows into one cohesive CLI tool.

*This is the first official stable release.*


## [0.10.2] - 2025-12-11

* * Stable tag now updates only when a new highest version is released.
* Debian package now includes sudo to ensure privilege escalation works reliably.
* Nix setup is significantly more resilient with retries, correct permissions, and better environment handling.
* AUR builder setup uses retries so yay installs succeed even under network instability.
* Nix flake installation now fails only on mandatory parts; optional outputs no longer block installation.


## [0.10.1] - 2025-12-11

* Fixed Debian\Ubuntu to pass container e2e tests


## [0.10.0] - 2025-12-11

**Mirror System**

* Added SSH mirror support including multi-push and remote probing
* Introduced mirror management commands and refactored the CLI parser into modules

**CI/CD**

* Migrated to reusable workflows with improved debugging instrumentation
* Made stable-tag automation reliable for workflow_run events and permissions
* Ensured deterministic test results by rebuilding all test containers with no-cache

**E2E and Container Tests**

* Fixed Git safe.directory handling across all containers
* Restored Dockerfile ENTRYPOINT to resolve Nix TLS issues
* Fixed missing volume errors and hardened the E2E runner
* Added full Nix flake E2E test matrix across all distro containers
* Disabled Nix sandboxing for cross-distro builds where required

**Nix and Python Environment**

* Unified Nix Python environment and introduced lazy CLI imports
* Ensured PyYAML availability and improved Python 3.13 compatibility
* Refactored flake.nix to remove side effects and rely on generic python3

**Packaging**

* Removed Debian’s hard dependency on Nix
* Restructured packaging layout and refined build paths
* Excluded assets from Arch PKGBUILD rsync
* Cleaned up obsolete ignore files

**Repository Layout**

* Restructured repository to align local, Nix-based, and distro-based build workflows
* Added Arch support and refined build/purge scripts


## [0.9.1] - 2025-12-10

* * Refactored installer: new `venv-create.sh`, cleaner root/user setup flow, updated README with architecture map.
* Split virgin tests into root/user workflows; stabilized Nix installer across distros; improved test scripts with dynamic distro selection and isolated Nix stores.
* Fixed repository directory resolution; improved `pkgmgr path` and `pkgmgr shell`; added full unit/E2E coverage.
* Removed deprecated files and updated `.gitignore`.


## [0.9.0] - 2025-12-10

* Introduce a virgin Arch-based Nix flake E2E workflow that validates pkgmgr’s full flake installation path using shared caches for faster and reproducible CI runs.


## [0.8.0] - 2025-12-10

* **v0.7.15 — Installer & Command Resolution Improvements**

* Introduced a unified **layer-based installer pipeline** with clear precedence (OS-packages, Nix, Python, Makefile).
* Reworked installer structure and improved Python/Nix/Makefile installers, including isolated Python venvs and refined flake-output handling.
* Fully rewrote **command resolution** with stronger typing, safer fallbacks, and explicit support for `command: null` to mark library-only repositories.
* Added extensive **unit and integration tests** for installer capability ordering, command resolution, and Nix/Python installer behavior.
* Expanded documentation with capability hierarchy diagrams and scenario matrices.
* Removed deprecated repository entries and obsolete configuration files.


## [0.7.14] - 2025-12-10

* Fixed the clone-all integration test so that `SystemExit(0)` from the proxy is treated as a successful command instead of a failure.


## [0.7.13] - 2025-12-10

### Fix tools path resolution and add tests

- Fixed a crash in `pkgmgr code` caused by missing `directory` metadata by introducing `_resolve_repository_path()` with proper fallbacks to `repositories_base_dir` / `repositories_dir`.
- Updated `explore`, `terminal` and `code` tool commands to use the new resolver.
- Improved VS Code workspace generation and path handling.
- Added unit & E2E tests for tool commands.


## [0.7.12] - 2025-12-09

* Fixed self refering alias during setup


## [0.7.11] - 2025-12-09

* test: fix installer unit tests for OS packages and Nix dev shell


## [0.7.10] - 2025-12-09

* Fixed test_install_pkgmgr_shallow.py


## [0.7.9] - 2025-12-09

* 'main' and 'master' are now both accepted as branches for branch close merge


## [0.7.8] - 2025-12-09

* Missing pyproject.toml doesn't lead to an error during release


## [0.7.7] - 2025-12-09

* Added TEST_PATTERN parameter to execute dedicated tests


## [0.7.6] - 2025-12-09

* Fixed pull --preview bug in e2e test


## [0.7.5] - 2025-12-09

* Fixed wrong directory permissions for nix


## [0.7.4] - 2025-12-09

* Fixed missing build in test workflow -> Tests pass now


## [0.7.3] - 2025-12-09

* Fixed bug: Ignored packages are now ignored


## [0.7.2] - 2025-12-09

* Implemented Changelog Support for Fedora and Debian


## [0.7.1] - 2025-12-09

* Fix floating 'latest' tag logic: dereference annotated target (vX.Y.Z^{}), add tag message to avoid Git errors, ensure best-effort update without blocking releases, and update unit tests (see ChatGPT conversation: https://chatgpt.com/share/69383024-efa4-800f-a875-129b81fa40ff).


## [0.7.0] - 2025-12-09

* Add Git helpers for branch sync and floating 'latest' tag in the release workflow, ensure main/master are updated from origin before tagging, and extend unit/e2e tests including 'pkgmgr release --help' coverage (see ChatGPT conversation: https://chatgpt.com/share/69383024-efa4-800f-a875-129b81fa40ff)


## [0.6.0] - 2025-12-09

* Expose DISTROS and BASE_IMAGE_* variables as exported Makefile environment variables so all build and test commands can consume them dynamically. By exporting these values, every Make target (e.g., build, build-no-cache, build-missing, test-container, test-unit, test-e2e) and every delegated script in scripts/build/ and scripts/test/ now receives a consistent view of the supported distributions and their base container images. This change removes duplicated definitions across scripts, ensures reproducible builds, and allows build tooling to react automatically when new distros or base images are added to the Makefile.


## [0.5.1] - 2025-12-09

* Refine pkgmgr release CLI close wiring and integration tests for --close flag (ChatGPT: https://chatgpt.com/share/69376b4e-8440-800f-9d06-535ec1d7a40e)


## [0.5.0] - 2025-12-09

* Add pkgmgr branch close subcommand, extend CLI parser wiring, and add unit tests for branch handling and version version-selection logic (see ChatGPT conversation: https://chatgpt.com/share/693762a3-9ea8-800f-a640-bc78170953d1)


## [0.4.3] - 2025-12-09

* Implement current-directory repository selection for release and proxy commands, unify selection semantics across CLI layers, extend release workflow with --close, integrate branch closing logic, fix wiring for get_repo_identifier/get_repo_dir, update packaging files (PKGBUILD, spec, flake.nix, pyproject), and add comprehensive unit/e2e tests for release and branch commands (see ChatGPT conversation: https://chatgpt.com/share/69375cfe-9e00-800f-bd65-1bd5937e1696)


## [0.4.2] - 2025-12-09

* Wire pkgmgr release CLI to new helper and add unit tests (see ChatGPT conversation: https://chatgpt.com/share/69374f09-c760-800f-92e4-5b44a4510b62)


## [0.4.1] - 2025-12-08

* Add branch close subcommand and integrate release close/editor flow (ChatGPT: https://chatgpt.com/share/69374f09-c760-800f-92e4-5b44a4510b62)


## [0.4.0] - 2025-12-08

* Add branch closing helper and --close flag to release command, including CLI wiring and tests (see https://chatgpt.com/share/69374aec-74ec-800f-bde3-5d91dfdb9b91)

## [0.3.0] - 2025-12-08

* Massive refactor and feature expansion:
- Complete rewrite of config loading system (layered defaults + user config)
- New selection engine (--string, --category, --tag)
- Overhauled list output (colored statuses, alias highlight)
- New config update logic + default YAML sync
- Improved proxy command handling
- Full CLI routing refactor
- Expanded E2E tests for list, proxy, and selection logic
Konversation: https://chatgpt.com/share/693745c3-b8d8-800f-aa29-c8481a2ffae1

## [0.2.0] - 2025-12-08

* Add preview-first release workflow and extended packaging support (see ChatGPT conversation: https://chatgpt.com/share/693722b4-af9c-800f-bccc-8a4036e99630)


## [0.1.0] - 2025-12-08

* Updated to correct version


## [0.1.0] - 2025-12-08

* Implement unified release helper with preview mode, multi-packaging version bumps, and new integration/unit tests (see ChatGPT conversation 2025-12-08: https://chatgpt.com/share/693722b4-af9c-800f-bccc-8a4036e99630)

