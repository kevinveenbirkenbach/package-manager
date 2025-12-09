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

