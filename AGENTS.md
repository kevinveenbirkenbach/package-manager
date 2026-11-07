# Agent Instructions

## Scope against the skills repository

package-manager holds deterministic code that an operator can run on its own,
without an agent: repository, branch, worktree, release, packaging and
development tooling. Agent coordination (claims, messages, queues, scores,
prompts, session data) belongs to the
[skills repository](https://github.com/kevinveenbirkenbach/skills), whose skills
stay thin wrappers that call `pkgmgr`.

- A new helper that a human could sensibly run alone goes here as a `pkgmgr`
  command, with its tests, never as a script inside a skill.
- Output that an agent filters further (claims, busy agents, scores) is
  emitted as `--json`; the filtering stays in the skill.
- When the split of a helper is unclear, the operator decides.

## Working copy

The installed `pkgmgr` may run straight from the main checkout, so a
half-edited tree breaks it for everyone. Edit only in a worktree
(`pkgmgr worktree up <branch>`), never in the main checkout.
