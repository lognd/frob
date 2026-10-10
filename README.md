<p align="center">
  <img src="https://raw.githubusercontent.com/lognd/frob/main/docs/assets/frob-banner.svg" alt="frob: a small green goblin in an aviator cap hunched over a crystal ball of glowing rune-code. The enforcement layer for agentic development." width="100%"/>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://github.com/lognd/frob/actions/workflows/ci.yml"><img src="https://github.com/lognd/frob/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
</p>

# frob

frob is a monorepo of three products built on one shared substrate (the
`gob-*` crates), written in Rust. This is v2 (0.532.0 and later); the Python
v1 line ended at 0.531.0 (see [docs/guides/upgrade-from-v1.md](docs/guides/upgrade-from-v1.md)).

| Product | What it does | Status |
|---|---|---|
| **frob** | The ticket goblin: a git-tracked ticket ledger, scope leases, per-ticket worktrees, cycles and milestones, evidence-gated close and land, `check` rules, release cuts. | Released, the main product. |
| **grimble** | The design goblin: checks code against a declared design model (`design/model.grmb`). | Preview until 0.533.0. |
| **crunk** | The design-system linter for CSS and design tokens. | Preview: the rule set is still empty. |

Self-hosting: this repository's tickets and gates are run by frob v2 built
from this tree (see [CONTRIBUTING.md](CONTRIBUTING.md)).

## What frob gives you

- **A ticket ledger in git.** Tickets live under `tickets/` as append-only
  event files, so concurrent branches merge instead of conflict. Tickets have
  types, priorities, story points, acceptance criteria and typed links.
- **Scope leases.** `frob work` leases a ticket's file globs and creates a
  worktree and branch for it; `frob check` fails a change outside the lease
  (rule SCOPE001).
- **Evidence-gated done.** Acceptance criteria are bound to measured evidence
  (`frob test`, `frob ticket evidence add --accepts N`); `frob land` refuses
  until every criterion is evidenced and the check is green.
- **Planning.** Cycles with capacity, milestones with exit criteria, a
  scrumban `frob board` with WIP limits.
- **Rules with a remedy.** Every finding names the command that fixes it, and
  every command answers in one JSON envelope (`--json`, the default when
  stdout is not a terminal) with stable exit codes.

## Install

From PyPI (the wheel carries the Rust executables, no Python modules):

```sh no-run
uv tool install frob
# or
pip install frob
```

The `frob` package depends on `grimble`, so both binaries arrive together.
Prebuilt archives of all three binaries (`frob`, `grimble`, `crunk`) for
Linux, macOS and Windows are attached to each release on
[GitHub](https://github.com/lognd/frob/releases). `crunk` is only in those
archives, not on PyPI. To build from a checkout, use the pinned toolchain in
`rust-toolchain.toml` and run `cargo build --release -p frob`.

Upgrading from v1? `pip install -U frob` moves you to v2, which has different
commands and a different ticket layout. Read
[docs/guides/upgrade-from-v1.md](docs/guides/upgrade-from-v1.md) first, or pin
`frob==0.531.0`.

## A first look

In any git repository with at least one commit:

```sh
frob --version
frob init
frob ticket new --title "Add multiply" --scope 'src/**' --points 2
frob ticket list
frob board
frob check
```

`frob init` writes `frob.toml` and `.gitattributes` (the ledger merge driver)
and ignores `.frob/`; commit them. A fresh `frob check` prints a few
"unresolved" lines for files with no language adapter, such as `frob.toml`;
they do not fail the gate.

The full loop (cycle, work, test, evidence, land, release status) is in
[docs/guides/quickstart.md](docs/guides/quickstart.md).

## grimble and crunk

Both follow the same conventions as frob: `--json`/`--text`, one envelope,
`check` and `doctor` verbs, and a config file at the repository root.

```sh
grimble init
grimble check
crunk doctor
```

`grimble init` writes `grimble.toml` and seeds `design/model.grmb`; `frob
check` runs a `grimble` or `crunk` it finds next to the `frob` binary or on
`PATH` and merges its findings. `crunk check` needs a `crunk.toml` first. See
[docs/crunk/README.md](docs/crunk/README.md) and
[docs/crunk/config.md](docs/crunk/config.md). grimble and crunk are previews:
their rule sets and verbs are still growing.

## Reference

- [docs/README.md](docs/README.md): the index of every document, with its status.
- [docs/guides/quickstart.md](docs/guides/quickstart.md): init to land.
- [docs/reference/cli/frob.md](docs/reference/cli/frob.md): every `frob` verb and flag, generated from the CLI (`cargo dev gen cli`).
- [docs/reference/config.md](docs/reference/config.md): every `frob.toml` key.
- [docs/reference/rules/](docs/reference/rules/): one page per check rule.
- [docs/guides/release.md](docs/guides/release.md): cutting a frob release.
- [docs/design/README.md](docs/design/README.md): the design set and decision log.
- [CHANGELOG.md](CHANGELOG.md): what shipped.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the ticket-queue workflow and the
evidence/close/land dance. Please also read the
[Code of Conduct](CODE_OF_CONDUCT.md). Found a security issue? See
[SECURITY.md](SECURITY.md) and do not file it as a public issue.
