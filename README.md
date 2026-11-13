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

### Worktrees and garbage collection

| Command | Does |
| --- | --- |
| `pkgmgr worktree up <branch> [--base REF] [--path DIR] [--pull REF ...] [--push BRANCH ...]` | Checks the branch out under `<directories.worktrees>/<host>/<owner>/<repo>/<branch>` or at `--path`, assigns a free slot, records the merge flow and runs the pinned `worktree-init` hook |
| `pkgmgr worktree flow [PATH] [--json]` | Shows the merge flow of the worktree at `PATH` (default: `.`) |
| `pkgmgr worktree flow set [PATH] (--pull REF ... \| --no-pull) (--push BRANCH ... \| --no-push) [--json]` | Replaces both lists of the merge flow |
| `pkgmgr worktree flow clear [PATH] [--json]` | Removes the merge flow |
| `pkgmgr worktree cleanup [--apply]` | Removes clean worktrees whose commits are merged or pushed: pinned `worktree-fini` hook, compose stack, checkout; the branch stays |
| `pkgmgr branch cleanup [--apply]` | Removes merged branches that no worktree holds, locally and on the remotes |
| `pkgmgr branch cleanup --local [--apply] [--json] [--merged-into REF]...` | Deletes only local branches whose tip is an ancestor of the remote-tracking default or of a `--merged-into` REF, each with `git update-ref --no-deref -d` against the planned sha and then its `branch.<name>` section in the repository's own config file (`git config --file <git common dir>/config`; a section it cannot remove is noted on the done item), also when the branch has an upstream or remote copy. Every git call of `--local` runs without any inherited `GIT_*` variable but `GIT_CEILING_DIRECTORIES`, which only narrows repository discovery, so a directory below a ceiling is never resolved to the repository above it; only the config reads of `deleteMerged` and of the upstreams run twice, both with the system config: once with the caller's `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM`, `GIT_CONFIG_PARAMETERS` and `GIT_CONFIG_COUNT` with its `GIT_CONFIG_KEY_<n>` and `GIT_CONFIG_VALUE_<n>`, once without any of them, without `XDG_CONFIG_HOME` and with `HOME` set to the passwd home, and a branch either read keeps stays, so the environment can add keeps but never remove one. A `--merged-into` REF must name exactly one branch or remote-tracking ref, as `git rev-parse --symbolic-full-name` resolves it, in every scanned repository git can read; `X~0`, `X^0`, `X@{0}`, a sha, a range or an unknown ref stops the run. The default comes from `origin`, or from the only remote when there is no `origin`: the ref `refs/remotes/<remote>/HEAD`, else `main`, else `master` resolves to, every symref step inside `refs/remotes/<remote>/`, so never a local branch or `HEAD`; without one, for example with several remotes and no `origin`, the repository is refused, also under `--merged-into`; so is one whose `refs`, `packed-refs`, `reftable`, `logs` or `logs/refs` is a symlink (git-new-workdir), one with a symlink anywhere below `refs/`, `reftable/` or `logs/refs/` (for example `refs/heads/team` linked to another clone's heads), one whose git dir is neither its git common dir nor directly under `<common>/worktrees/` (a registration moved elsewhere), or one whose git output is not UTF-8. The repository is the one the current directory belongs to, also in a submodule or with a separate git dir; one whose main worktree belongs to another repository (`core.worktree`), whose git dir is neither its git common dir nor directly under `<common>/worktrees/`, or whose path is not UTF-8 is refused with exit 2. Skips a symbolic branch, every branch a symbolic ref anywhere under `refs/` (also a tag or remote-tracking one) or under the main worktree's or any registration's `refs/worktree/` points to, a branch that is itself a `--merged-into` target, a branch a worktree holds or that the HEAD of the main repository or of any `worktrees/<id>` registration names (also one `git worktree list` omits or whose id is no valid ref name, read through `git --git-dir=<dir> symbolic-ref HEAD`, so also under reftable), one a rebase or bisect in any worktree works on, one merged only by patch or PR, and, as `git branch --delete-merged` keeps them, one whose `branch.<name>.deleteMerged` is false in the config of any worktree (also its `config.worktree` or an `includeIf "onbranch:..."` file) or in the system config file, and the local upstream, as git's `%(upstream)` resolves it in any worktree, of any branch that stays, also of one that `--branch` or `--exclude` leaves out, each shown as kept with its reason; these holds are read through the git common dir, whichever worktree is scanned, and a registration, symbolic ref, HEAD or state file they cannot read refuses the repository; when a repository vanishes, moves or stops being readable, or its default or a `--merged-into` target stops resolving mid-run, its later items are skipped with that reason and the plan is still printed. A repository git or the filesystem fails on while planning (for example a dangling `.git` file under `--all`) is refused with that reason and the run goes on. The plan, refused repositories included, is printed (as JSON with `--json`), and the run exits 1 when an item failed, else 2 when a repository was refused, else 0. It stops with a message on stderr, no plan and exit 2 in exactly these cases: without `--all`, the current directory is not inside a git repository, its git dir is neither its git common dir nor directly under `<common>/worktrees/`, its main worktree belongs to another repository (`core.worktree`), or its path or git output is not UTF-8; `--apply` outside the host PID namespace; a `--merged-into` REF refused as above; a `--branch` that matches no item. Meant for working clones and their worktrees, not for a bare server repository. Not mirrored from `git branch --delete-merged`: git also keeps a branch whose push would update its own upstream; `--local` does not. Known residuals: a worktree, rebase or symbolic ref that starts holding a branch between its last re-check and its `update-ref -d` is not seen; a `deleteMerged` or upstream config change after the plan is not re-checked before the delete; an entry under `<git common dir>/worktrees/` that is no git dir (for example an empty leftover) refuses the repository. Reads no forge token and never fetches, pushes, deletes a remote branch, runs docker or repository hooks, touches a worktree, compose stack, volume or image, or refreshes the branch tree file (rerun `pkgmgr branch tree` for that) |
| `pkgmgr branch tree [--format json\|yaml] [--output FILE]` | Writes every managed repository's branches and worktrees with their cleanup state, without fetching |
| `pkgmgr gc [--all] [--apply]` | Both cleanups in one pass, for the current repository or every managed one |
| `pkgmgr gc --report [--all] [--root DIR] [--threshold-mb MB] [--docker] [--json]` | Read-only disk inventory: worktree sizes, changes a cleanup would keep, `--root` children, core dumps, docker usage, free space per filesystem |
| `pkgmgr worktree orphans --stale-days N --top N` | Lists merged and abandoned branches and worktrees with a proposal each |

A hook runs only when the `worktree_hooks` config pins its command under the
`<provider>/<account>/<repository>` of a repository managed in the pkgmgr
config, and only for that repository's directory; origin's URL, which the
repository's own config sets, never selects a pin. `{path}` and `{slot}` are
replaced; a
`worktree-init` or `worktree-fini` target in the repository's Makefile is
reported, never run, because an agent may have written it. The pinned program
must be an absolute path or a root-owned command on a `PATH` entry that root
owns and no group or other user can write, up to `/`, so a binary planted in a
user-writable directory such as a virtualenv never runs. The Nix store never
counts: it is group-writable, and any user can have the daemon build
root-owned content there, so pin an absolute path on Nix. A bare name runs as
the resolved file that was checked. Inside a user namespace other than the
initial one, root means the overflow uid, under which the real root's files
show there, as do those of every other unmapped owner. Outside such a
namespace a directory on a nosuid mount, where udisks2 and FUSE put user
mounts, never counts as root's. The hook runs with
stdin closed, only those `PATH` entries and a 30 minute timeout. Removal walks to
the worktree without following a symbolic link and skips a worktree path that
is not its own realpath. A pinned command that reads repository files, such as `make` or a
script in the repository, trusts the worktree's content, tracked or ignored.

Every cleanup is a dry run until `--apply`, and `--json` prints the plan for
other tools. The [agent skills](https://github.com/kevinveenbirkenbach/skills)
wrap these commands; see [AGENTS.md](AGENTS.md) for the split.

#### Merge flow

Every worktree can carry a merge flow that scripts and skills read: `pull`
lists the refs merged into the branch, in order, before a gate, deploy or
merge; `push` lists the branches the branch is merged into, in order, when it
is finished, each then pushed by the operator. It lives in
`pkgmgr/flow.yml` inside the worktree's own git directory (`.git` of the main
worktree, `<common>/worktrees/<id>` of a linked one), so it is never committed
and goes with the worktree:

```yaml
version: 1
branch: feature/x
pull:
  - origin/main
  - store-i18n
push:
  - feature/iam-profile-rbac
  - production
```

`branch` is the branch the flow was set on; another current branch shows as a
warning. `worktree up` records `--pull` and `--push`; without them pull is
the base the worktree came from and push that base's local branch
(`origin/main` gives `main`). `flow set` needs each list or
its `--no-pull`/`--no-push`, and writes atomically into a `pkgmgr/` of mode
0700. Every entry must pass `git check-ref-format --branch` and must not start
with `-`; a remote-tracking name such as `origin/main` passes. An invalid name
exits 2 and writes nothing. A flow file that is a symbolic link, no regular
file, larger than 64 KiB or malformed reads as `invalid`, with empty lists and
a warning, and is never followed.

`flow --json` prints `worktree` and `git_dir` (absolute paths), `branch` (the
current branch, `null` when detached), `flow_branch` (the file's `branch`),
`pull`, `push`, `source` (`file`, `none` or `invalid`) and `warnings`; it
exits 0 also without a flow, 2 when `PATH` is not a git worktree. In
`pkgmgr branch tree` every item carries `flow`: `{"pull", "push", "source"}`,
or `null` without a worktree or a flow; flow warnings join the repository's
`warnings`.

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

#### Container images

One image per distribution, each installing PKGMGR as a distro-native package
on top of the matching base image from
[base-images](https://github.com/kevinveenbirkenbach/base-images). Every image
is a manifest list covering `linux/amd64` and `linux/arm64`.

All images live under `ghcr.io/kevinveenbirkenbach/`:

| Tag                                   | Contains                                                  |
| ------------------------------------- | --------------------------------------------------------- |
| `pkgmgr-<distro>:latest`              | newest build of the newest release on `main`              |
| `pkgmgr-<distro>:stable`              | newest build of the release the git tag `stable` marks    |
| `pkgmgr-<distro>:<major>`             | newest build of the newest release of that major          |
| `pkgmgr-<distro>:<major>.<minor>`     | newest build of the newest release of that minor          |
| `pkgmgr-<distro>:<version>`           | newest build of that release                              |
| `pkgmgr-<distro>:<version>.<unix-ts>` | one build, never moves                                    |

`<distro>` is one of `arch`, `debian`, `ubuntu`, `fedora`, `centos`. The Arch
image is published without the suffix as well, so `pkgmgr:stable` and
`pkgmgr-arch:stable` are the same image.

`<version>` is the PKGMGR release and `<unix-ts>` the build time, so
`2.3.0.1767225600` is a full version an updater can order and pin. Every tag of
one build points at the same image.

`stable` moves only once "Mark stable commit" has moved the git tag `stable`,
which it does after every test of that release passed. Every day at 03:00 UTC,
after the daily 00:00 UTC build of base-images, and on demand through the
workflow's manual trigger, two releases are rebuilt on the newest base image:

- the newest `vX.Y.Z` release on `main`, moving `latest`, its prefixes and
  `<version>`, and adding `<version>.<unix-ts>`;
- the release the git tag `stable` marks, when that is an older one, moving
  `stable` and `<version>`, adding its own `<version>.<unix-ts>`, and moving a
  prefix only while it is still the newest release of that prefix.

With newest `2.4.0` and stable `2.3.0`, `2.4.0` takes `latest`, `2` and `2.4`,
and `2.3.0` takes `stable` and `2.3`. A security update in base-images thereby
reaches whoever pinned a major, a minor, a release or follows `stable`.

Each release is compared with its own published `<version>`. A rebuild whose
installed packages equal it pushes nothing, since a new timestamp tag would make
every pin bump for no change; a tag of that release that does not show the
published build yet, such as `stable` right after "Mark stable commit", is moved
without a new timestamp.

A rebuild runs the build scripts of the release it rebuilds, not those of
`main`, so the skip and the tag rules above only hold for releases tagged after
this scheme landed. The scripts of an earlier release know no aliases: its merge
step fails and leaves its tags where they are, until a newer release replaces
it as the newest and the stable one.

For a clean environment that carries the system dependencies but no PKGMGR,
pull `base-<distro>` from
[base-images](https://github.com/kevinveenbirkenbach/base-images) directly.

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
