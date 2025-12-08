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

