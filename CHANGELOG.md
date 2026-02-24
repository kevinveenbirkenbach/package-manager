## [1.12.2] - 2026-02-24

* Removed infinito-sphinx package


## [1.12.1] - 2026-02-14

* pkgmgr now prefers distro-managed nix binaries on Arch before profile/PATH resolution, preventing libllhttp mismatch failures after pacman system upgrades.


## [1.12.0] - 2026-02-08

* Adds explicit concurrency groups to the CI and mark-stable workflows to prevent overlapping runs on the same branch and make pipeline execution more predictable.


## [1.11.2] - 2026-02-08

* Removes the v* tag trigger from the mark-stable workflow so it runs only on branch pushes and avoids duplicate executions during releases.


## [1.11.1] - 2026-02-08

* Implements pushing the branch and the version tag together in a single command so the CI release workflow can reliably detect the version tag on HEAD.


## [1.11.0] - 2026-01-21

* Adds a dedicated slim Docker image for pkgmgr and publishes slim variants for all supported distros.


## [1.10.0] - 2026-01-20

* Introduce safe verbose image cleanup to reduce Docker image size and build artifacts

## [1.9.5] - 2026-01-16

* Release patch: improve git pull error diagnostics


## [1.9.4] - 2026-01-13

* fix(ci): replace sudo with su for user switching to avoid PAM failures in minimal container images


## [1.9.3] - 2026-01-07

* Made the Nix dependency optional on non-x86_64 architectures to avoid broken Arch Linux ARM repository packages.


## [1.9.2] - 2025-12-21

* Default configuration files are now packaged and loaded correctly when no user config exists, while fully preserving custom user configurations.


## [1.9.1] - 2025-12-21

* Fixed installation issues and improved loading of default configuration files.


## [1.9.0] - 2025-12-20

* * New ***mirror visibility*** command to set remote Git repositories to ***public*** or ***private***.
* New ***--public*** flag for ***mirror provision*** to create repositories and immediately make them public.
* All configured git mirrors are now provisioned.


## [1.8.7] - 2025-12-19

* * **Release version updates now correctly modify ***pyproject.toml*** files that follow PEP 621**, ensuring the ***[project].version*** field is updated as expected.
* **Invalid or incomplete ***pyproject.toml*** files are now handled gracefully** with clear error messages instead of abrupt process termination.
* **RPM spec files remain compatible during releases**: existing macros such as ***%{?dist}*** are preserved and no longer accidentally modified.


## [1.8.6] - 2025-12-17

* Prevent Rate Limits during GitHub Nix Setups


## [1.8.5] - 2025-12-17

* * Clearer Git error handling, especially when a directory is not a Git repository.
* More reliable repository verification with improved commit and GPG signature checks.
* Better error messages and overall robustness when working with Git-based workflows.


## [1.9.0] - 2025-12-17

* Automated release.


## [1.8.4] - 2025-12-17

* * Made pkgmgr’s base-layer role explicit by standardizing the Docker/CI mount path to *`/opt/src/pkgmgr`*.


## [1.8.3] - 2025-12-16

* MIRRORS now supports plain URL entries, ensuring metadata-only sources like PyPI are recorded without ever being added to the Git configuration.


## [1.8.2] - 2025-12-16

* * ***pkgmgr tools code*** is more robust and predictable: it now fails early with clear errors if VS Code is not installed or a repository is not yet identified.


## [1.8.1] - 2025-12-16

* * Improved stability and consistency of all Git operations (clone, pull, push, release, branch handling) with clearer error messages and predictable preview behavior.
* Mirrors are now handled cleanly: only valid Git remotes are used for Git operations, while non-Git URLs (e.g. PyPI) are excluded, preventing broken or confusing repository configs.
* GitHub authentication is more robust: tokens are automatically resolved via the GitHub CLI (`gh`), invalid stored tokens are replaced, and interactive prompts occur only when necessary.
* Repository creation and release workflows are more reliable, producing cleaner Git configurations and more predictable version handling.


## [1.8.0] - 2025-12-15

* *** New Features: ***
- **Silent Updates**: You can now use the `--silent` flag during installs and updates to suppress error messages for individual repositories and get a single summary at the end. This ensures the process continues even if some repositories fail, while still preserving interactive checks when not in silent mode.
- **Repository Scaffolding**: The process for creating new repositories has been improved. You can now use templates to scaffold repositories with a preview and automatic mirror setup.

*** Bug Fixes: ***
- **Pip Installation**: Pip is now installed automatically on all supported systems. This includes `python-pip` for Arch and `python3-pip` for CentOS, Debian, Fedora, and Ubuntu, ensuring that pip is available for Python package installations.
- **Pacman Keyring**: Fixed an issue on Arch Linux where package installation would fail due to missing keys. The pacman keyring is now properly initialized before installing packages.


## [1.7.2] - 2025-12-15

* * Git mirrors are now resolved consistently (origin → MIRRORS file → config → default).
* The `origin` remote is always enforced to use the primary URL for both fetch and push.
* Additional mirrors are added as extra push targets without duplication.
* Local and remote mirror setup behaves more predictably and consistently.
* Improved test coverage ensures stable origin and push URL handling.


## [1.7.1] - 2025-12-14

* Patched package-manager to kpmx to publish on pypi


## [1.7.0] - 2025-12-14

* * New *pkgmgr publish* command to publish repository artifacts to PyPI based on the *MIRRORS* file.
* Automatically selects the current repository when no explicit selection is given.
* Publishes only when a semantic version tag is present on *HEAD*; otherwise skips with a clear info message.
* Supports non-interactive mode for CI environments via *--non-interactive*.


## [1.6.4] - 2025-12-14

* * Improved reliability of Nix installs and updates, including automatic resolution of profile conflicts and better handling of GitHub 403 rate limits.
* More stable launcher behavior in packaged and virtual-env setups.
* Enhanced mirror and remote handling: repository owner/name are derived from URLs, with smoother provisioning and clearer credential handling.
* More reliable releases and artifacts due to safer CI behavior when no version tag is present.


## [1.6.3] - 2025-12-14

* ***Fixed:*** Corrected repository path resolution so release and version logic consistently use the canonical packaging/* layout, preventing changelog and packaging files from being read or updated from incorrect locations.


## [1.6.2] - 2025-12-14

* **pkgmgr version** now also shows the installed pkgmgr version when run outside a repository.


## [1.6.1] - 2025-12-14

* * Added automatic retry handling for GitHub 403 / rate-limit errors during Nix flake installs (Fibonacci backoff with jitter).


## [1.6.0] - 2025-12-14

* *** Changed ***
- Unified update handling via a single top-level `pkgmgr update` command, removing ambiguous update paths.
- Improved update reliability by routing all update logic through a central UpdateManager.
- Renamed system update flag from `--system-update` to `--system` for clarity and consistency.
- Made mirror handling explicit and safer by separating setup, check, and provision responsibilities.
- Improved credential resolution for remote providers (environment → keyring → interactive).

*** Added ***
- Optional system updates via `pkgmgr update --system` (Arch, Debian/Ubuntu, Fedora/RHEL).
- `pkgmgr install --update` to force re-running installers and refresh existing installations.
- Remote repository provisioning for mirrors on supported providers.
- Extended end-to-end test coverage for update and mirror workflows.

*** Fixed ***
- Resolved “Unknown repos command: update” errors after CLI refactoring.
- Improved Nix update stability and reduced CI failures caused by transient rate limits.


## [1.5.0] - 2025-12-13

* - Commands now show live output while running, making long operations easier to follow
- Error messages include full command output, making failures easier to understand and debug
- Deinstallation is more complete and predictable, removing CLI links and properly cleaning up repositories
- Preview mode is more trustworthy, clearly showing what would happen without making changes
- Repository configuration problems are detected earlier with clear, user-friendly explanations
- More consistent behavior across different Linux distributions
- More reliable execution in Docker containers and CI environments
- Nix-based execution works more smoothly, especially when running as root or inside containers
- Existing commands, scripts, and workflows continue to work without any breaking changes


## [1.4.1] - 2025-12-12

* Fixed stable release container publishing


## [1.4.0] - 2025-12-12

**Docker Container Building**

* New official container images are automatically published on each release.
* Images are available per distribution and as a default Arch-based image.
* Stable releases now provide an additional `stable` container tag.


## [1.3.1] - 2025-12-12

* Updated documentation with better run and installation instructions


## [1.3.0] - 2025-12-12

**Stability & CI hardening**

* Stabilized Nix resolution and global symlink handling across Arch, CentOS, Debian, and Ubuntu
* Ensured Nix works reliably in CI, sudo, login, and non-login shells without overriding distro-managed paths
* Improved error handling and deterministic behavior for non-root environments
* Refactored Docker and CI workflows for reproducible multi-distro virgin tests
* Made E2E tests more realistic by executing real CLI commands
* Fixed Python compatibility and missing dependencies on affected distros


## [1.2.1] - 2025-12-12

**Changed**

* Split container tests into *virtualenv* and *Nix flake* environments to clearly separate Python and Nix responsibilities.

**Fixed**

* Fixed Nix installer permission issues when running under a different user in containers.
* Improved reliability of post-install Nix initialization across all distro packages.

**CI**

* Replaced generic container tests with explicit environment checks.
* Validate Nix availability via *nix flake* tests instead of Docker build-time side effects.


## [1.2.0] - 2025-12-12

**Release workflow overhaul**

* Introduced a fully structured release workflow with clear phases and safeguards
* Added preview-first releases with explicit confirmation before execution
* Automatic handling of *latest* tag when a release is the newest version
* Optional branch closing after successful releases with interactive confirmation
* Improved safety by syncing with remote before any changes
* Clear separation of concerns (workflow, git handling, prompts, versioning)


## [1.1.0] - 2025-12-12

* Added *branch drop* for destructive branch deletion and introduced *--force/-f* flags for branch close and branch drop to skip confirmation prompts.


## [1.0.0] - 2025-12-11

**Official Stable Release 🎉**

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

* Refactored installer: new `venv-create.sh`, cleaner root/user setup flow, updated README with architecture map.
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

* Fix floating 'latest' tag logic
* dereference annotated target (vX.Y.Z^{})
* add tag message to avoid Git errors
* ensure best-effort update without blocking releases

## [0.7.0] - 2025-12-09

* Add Git helpers for branch sync and floating 'latest' tag in the release workflow
* ensure main/master are updated from origin before tagging

## [0.6.0] - 2025-12-09

* Consistent view of the supported distributions and their base container images. 

## [0.5.1] - 2025-12-09

* Refine pkgmgr release CLI close wiring and integration tests for --close flag


## [0.5.0] - 2025-12-09

* Add pkgmgr branch close subcommand, extend CLI parser wiring

## [0.4.3] - 2025-12-09

* Implement current-directory repository selection for release and proxy commands, unify selection semantics across CLI layers, extend release workflow with --close, integrate branch closing logic, fix wiring for get_repo_identifier/get_repo_dir, update packaging files (PKGBUILD, spec, flake.nix, pyproject)

## [0.4.2] - 2025-12-09

* Wire pkgmgr release CLI to new helpe


## [0.4.1] - 2025-12-08

* Add branch close subcommand and integrate release close/editor flow

## [0.4.0] - 2025-12-08

* Add branch closing helper and --close flag to release command

## [0.3.0] - 2025-12-08

* Massive refactor and feature expansion:
- Complete rewrite of config loading system (layered defaults + user config)
- New selection engine (--string, --category, --tag)
- Overhauled list output (colored statuses, alias highlight)
- New config update logic + default YAML sync
- Improved proxy command handling
- Full CLI routing refactor

## [0.2.0] - 2025-12-08

* Add preview-first release workflow and extended packaging support

## [0.1.0] - 2025-12-08

* Updated to correct version


## [0.1.0] - 2025-12-08

* Implement unified release helper with preview mode, multi-packaging version bumps