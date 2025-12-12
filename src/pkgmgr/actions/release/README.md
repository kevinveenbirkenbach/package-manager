# Release Action

This module implements the `pkgmgr release` workflow.

It provides a controlled, reproducible release process that:
- bumps the project version
- updates all supported packaging formats
- creates and pushes Git tags
- optionally maintains a floating `latest` tag
- optionally closes the current branch

The implementation is intentionally explicit and conservative to avoid
accidental releases or broken Git states.

---

## What the Release Command Does

A release performs the following high-level steps:

1. Synchronize the current branch with its upstream (fast-forward only)
2. Determine the next semantic version
3. Update all versioned files
4. Commit the release
5. Create and push a version tag
6. Optionally update and push the floating `latest` tag
7. Optionally close the current branch

All steps support **preview (dry-run)** mode.

---

## Supported Files Updated During a Release

If present, the following files are updated automatically:

- `pyproject.toml`
- `CHANGELOG.md`
- `flake.nix`
- `PKGBUILD`
- `package-manager.spec`
- `debian/changelog`

Missing files are skipped gracefully.

---

## Git Safety Rules

The release workflow enforces strict Git safety guarantees:

- A `git pull --ff-only` is executed **before any file modifications**
- No merge commits are ever created automatically
- Only the current branch and the newly created version tag are pushed
- `git push --tags` is intentionally **not** used
- The floating `latest` tag is force-pushed only when required

---

## Semantic Versioning

The next version is calculated from existing Git tags:

- Tags must follow the format `vX.Y.Z`
- The release type controls the version bump:
  - `patch`
  - `minor`
  - `major`

The new tag is always created as an **annotated tag**.

---

## Floating `latest` Tag

The floating `latest` tag is handled explicitly:

- `latest` is updated **only if** the new version is the highest existing version
- Version comparison uses natural version sorting (`sort -V`)
- `latest` always points to the commit behind the version tag
- Updating `latest` uses a forced push by design

This guarantees that `latest` always represents the highest released version,
never an older release.

---

## Preview Mode

Preview mode (`--preview`) performs a full dry-run:

- No files are modified
- No Git commands are executed
- All intended actions are printed

Example preview output includes:
- version bump
- file updates
- commit message
- tag creation
- branch and tag pushes
- `latest` update (if applicable)

---

## Interactive vs Forced Mode

### Interactive (default)

1. Run a preview
2. Ask for confirmation
3. Execute the real release

### Forced (`--force`)

- Skips preview and confirmation
- Skips branch deletion prompts
- Executes the release immediately

---

## Branch Closing (`--close`)

When `--close` is enabled:

- `main` and `master` are **never** deleted
- Other branches:
  - prompt for confirmation (`y/N`)
  - can be skipped using `--force`
- Branch deletion happens **only after** a successful release

---

## Execution Flow (ASCII Diagram)

```

+---------------------+
| pkgmgr release      |
+----------+----------+
|
v
+---------------------+
| Detect branch       |
+----------+----------+
|
v
+------------------------------+
| git fetch / pull --ff-only   |
+----------+-------------------+
|
v
+------------------------------+
| Determine next version       |
+----------+-------------------+
|
v
+------------------------------+
| Update versioned files       |
+----------+-------------------+
|
v
+------------------------------+
| Commit release               |
+----------+-------------------+
|
v
+------------------------------+
| Create version tag (vX.Y.Z)  |
+----------+-------------------+
|
v
+------------------------------+
| Push branch + version tag    |
+----------+-------------------+
|
v
+---------------------------------------+
| Is this the highest version?           |
+----------+----------------------------+
|
yes  |  no
|
v
+------------------------------+        +----------------------+
| Update & push `latest` tag   |        | Skip `latest` update |
+----------+-------------------+        +----------------------+
|
v
+------------------------------+
| Close branch (optional)      |
+------------------------------+

```

---

## Design Goals

- Deterministic and reproducible releases
- No implicit Git side effects
- Explicit tag handling
- Safe defaults for interactive usage
- Automation-friendly forced mode
- Clear separation of concerns:
  - `workflow.py` – orchestration
  - `git_ops.py` – Git operations
  - `prompts.py` – user interaction
  - `versioning.py` – SemVer logic

---

## Summary

`pkgmgr release` is a **deliberately strict** release mechanism.

It trades convenience for safety, traceability, and correctness — making it
suitable for both interactive development workflows and fully automated CI/CD
