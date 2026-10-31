<p align="center">
  <img src="https://raw.githubusercontent.com/lognd/frob/main/docs/assets/frob-banner.svg" alt="frob: a small green goblin in an aviator cap hunched over a crystal ball of glowing rune-code. The enforcement layer for agentic development." width="100%"/>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License: MIT"></a>
  <a href="https://github.com/lognd/frob/actions/workflows/ci.yml"><img src="https://github.com/lognd/frob/actions/workflows/ci.yml/badge.svg" alt="CI status"></a>
</p>

# frob

Status: current
Owner: frob
Decisions: none
Audience: user

frob is a monorepo of three products built on one shared substrate (the
`gob-*` crates), written in Rust. This is v2 (0.532.0 and later). The Python
v1 line ended at 0.531.0; see [docs/guides/upgrade-from-v1.md](docs/guides/upgrade-from-v1.md)
and the archived [CHANGELOG-v1.md](CHANGELOG-v1.md).

| Product | What it does | Status |
|---|---|---|
| **frob** | The ticket goblin: a git-tracked ticket ledger, scope leases, per-ticket worktrees, cycles and milestones, evidence-gated close and land, `check` rules, release cuts. | Released (0.532.0). The main product. |
| **grimble** | The design goblin: checks code against a declared design model (`design/model.grmb`). | Preview (0.532.0). Its `--version` says preview until 0.533.0. |
| **crunk** | The design-system linter for CSS and design tokens (`crunk.toml`). | Preview (0.532.0). Its rules are listed in [docs/crunk/rules/README.md](docs/crunk/rules/README.md). |

crunk is developed in this repository, in the `crunk-*` crates. The separate
`lognd/crunk` repository is archived. The PyPI project `crunk` (0.1.x) is the
old Python package from that repository; the Rust crunk is not published to PyPI.

Self-hosting: this repository's tickets and gates are run by frob v2 built
from this tree (see [CONTRIBUTING.md](CONTRIBUTING.md)).

## What frob gives you

- **A ticket ledger in git.** Tickets are append-only event files. Fresh
  repositories commit them to the code branch; `[tickets] ref_mode = "orphan"`
  moves them to the `frob-tickets` branch, so concurrent branches merge instead
  of conflict ([docs/guides/ticket-branch.md](docs/guides/ticket-branch.md)).
  Tickets have types, priorities, story points, acceptance criteria and typed links.
- **Scope leases.** `frob work` leases a ticket's file globs and creates a
  worktree and branch for it. `frob check` reports a change outside the lease
  as rule SCOPE001 ([docs/reference/rules/SCOPE001.md](docs/reference/rules/SCOPE001.md)).
- **Evidence-gated done.** Acceptance criteria are bound to measured evidence
  (`frob test`, or `frob ticket evidence add --accepts N`). `frob land` refuses
  until every criterion is evidenced and the check is green.
- **Planning.** Cycles with capacity, milestones with exit criteria, and a
  scrumban `frob board` with WIP limits.
- **Next steps in every answer.** Findings suggest the next command to run, and
  every command answers with one JSON envelope (`--json`, the default when
  stdout is not a terminal). Exit codes are one table ([docs/design/cli.md](docs/design/cli.md)).

## Install

From PyPI the `frob` wheel carries the Rust executables and depends on
`grimble`, so both binaries arrive together:

```sh no-run
uv tool install frob
# or
pip install frob
```

Prebuilt archives of `frob`, `grimble` and `crunk` for Linux, macOS and Windows
are attached to each release on [GitHub](https://github.com/lognd/frob/releases).
`crunk` is only in those archives in v2, not on PyPI. To build from a checkout,
use the toolchain pinned in `rust-toolchain.toml` and run
`cargo build --release -p frob-cli`; the binary is `target/release/frob`.

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
and ignores `.frob/`; commit them. A fresh `frob check` on a repository with
no tickets passes. A file with no language adapter is reported as "unresolved"
and does not fail the gate. A new ticket with no parent story makes `frob check`
report planning findings (for example PM007, PM032 and PM033) until the ticket
is placed in a story and the ready queue is larger.

The full loop (cycle, work, test, evidence, land, release status) is in
[docs/guides/quickstart.md](docs/guides/quickstart.md).

## grimble and crunk

Both follow the same conventions as frob: `--json`/`--text`, one JSON envelope,
a `check` verb, a `doctor` verb and a config file at the repository root.

```sh no-run
grimble init
grimble check
crunk init
crunk check
```

`grimble init` writes `grimble.toml` and seeds `design/model.grmb`. `crunk init`
scaffolds `crunk.toml`, which `crunk check` needs. `frob check` runs the
`grimble` and `crunk` binaries it finds next to `frob` or on `PATH` and merges
their findings. grimble and crunk are previews: their rule sets and verbs are
still growing. See [docs/guides/grimble.md](docs/guides/grimble.md) and
[docs/crunk/README.md](docs/crunk/README.md).

## Reference

- [docs/README.md](docs/README.md): the index of every document, with its status.
- [docs/guides/quickstart.md](docs/guides/quickstart.md): init to land.
- [docs/reference/cli/frob.md](docs/reference/cli/frob.md): every `frob` verb and flag (generated).
- [docs/reference/config.md](docs/reference/config.md): every `frob.toml` key (generated).
- [docs/reference/rules/](docs/reference/rules/): one page per check rule (generated).
- [docs/guides/release.md](docs/guides/release.md): cutting a frob release.
- [docs/design/README.md](docs/design/README.md): the design set.
- [CHANGELOG.md](CHANGELOG.md): what shipped in v2. [CHANGELOG-v1.md](CHANGELOG-v1.md) is the archived v1 history.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the ticket-queue workflow and the
evidence/close/land dance. Please also read the
[Code of Conduct](CODE_OF_CONDUCT.md). Found a security issue? See
[SECURITY.md](SECURITY.md) and do not file it as a public issue.
