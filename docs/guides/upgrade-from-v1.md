# Upgrade from frob v1 to v2

Status: current
Owner: frob
Decisions: none
Audience: user

How-to guide (Diataxis: task). Read this if you use frob 0.531.0 or earlier,
or if you have never seen v2 and want to know what the 0.532.0 upgrade does.

frob 0.532.0 is the v2 rewrite, written in Rust. It replaces v1 on upgrade:
installing or upgrading the `frob` package after 0.531.0 gives you v2. The
release notes lead the 0.532.0 section of [CHANGELOG.md](../../CHANGELOG.md);
v1's history is in [CHANGELOG-v1.md](../../CHANGELOG-v1.md).

## Stay on v1

v1's last release is 0.531.0 on PyPI. Pin it so nothing upgrades you.

```sh
uv tool install frob==0.531.0
```

```sh
pip install frob==0.531.0
```

Notes:

- v1 needs Python 3.11 or newer (the package metadata says `>=3.11`).
- With uv, the pin is recorded in the tool receipt, and `uv tool upgrade frob`
  then reports "Nothing to upgrade" and hints that `frob` is pinned. To move to
  v2 later, run `uv tool install frob@latest`.
- With pip, the pin only applies to that command. A later `pip install -U frob`
  upgrades to v2 once 0.532.0 is published, so keep the pin in your
  requirements file or constraints file.
- Pin it in CI too, or a fresh CI image installs v2.

## What changed

| | v1 (0.531.0 and earlier) | v2 (0.532.0 and later) |
|---|---|---|
| Implementation | Python package with native helper wheels | Rust binary; the PyPI wheel only carries executables, no Python modules |
| Install | `pip` or `uv tool` | the same `frob` package name; GitHub release archives, configured for five targets (aarch64 and x86_64 macOS, aarch64 and x86_64 Linux, x86_64 Windows) |
| Ticket ledger | `tickets/T-NNNN/ticket.md`, YAML front matter that commands edit in place | `tickets/<ULID>/ticket.md` plus append-only `events/<ULID>.toml` files; `ticket.md` is the folded result |
| Ticket ids | `T-0042` | a ULID, shown as a handle such as `~P4EENQH`; imported v1 ids stay usable as aliases |
| Ticket states | queued, planned, in-progress, done, dropped, archived | categories triage, todo, in-progress, done, with an outcome on done tickets |
| Merging the ledger | a ledger merge driver (`frob ticket merge-driver` exists in v1) | a merge driver `frob-ledger` (installed by `frob init`) that unions events and refolds |
| Output | text, with `--json` on verbs such as `check` and `test` | one JSON envelope on every verb; JSON when stdout is not a terminal, text on a terminal (`--text`, `--json` force one) |
| Exit codes | not compared here | 0 ok, 1 negative (a finding), 2 usage, 3 refused, 4 internal |
| Release flow | `frob release stamp/check/sync` (semver from the API graph) | milestones, `frob release status/cut`, CHANGELOG compiled from `changelog.d` fragments |

v2 does not have every v1 verb. The mapping table below lists what has a
counterpart; everything else is absent from 0.532.0.

## Command mapping

v2 commands below were checked against `frob --help` and each subcommand's
`--help` of the v2 binary. v1 commands were checked against v1's `frob --help`
and `frob ticket --help`.

| v1 | v2 | Notes |
|---|---|---|
| `frob ticket new --kind K --title T` | `frob ticket new --type T --title T` | v1 kinds feature and ux are type `task` in v2; v2 adds epic, story, chore, custom |
| `frob ticket list`, `show`, `doable`, `brief`, `contention` | `frob ticket list`, `show`, `doable`; `frob ticket show --format md`; `frob lease list --contention` | `brief` is `show --format md` and `contention` is `lease list --contention`; `list` filters are `--category`, `--type`, `--parent`, `--label`, `--blocked` |
| `frob ticket board` | `frob board` | columns by category with WIP limits |
| `frob ticket work ID` | `frob work TICKET` | leases the ticket, creates its worktree and branch; `--steal --reason` takes a held lease |
| `frob ticket start ID` | `frob work --here TICKET` | leases for this checkout, no new worktree |
| `frob ticket requeue ID` | `frob requeue --reason TEXT TICKET` | the reason is required |
| `frob ticket land` | `frob land [TICKET]` | `--dry-run`, `--push`, `--keep-worktree` |
| `frob ticket close ID` | `frob ticket close --outcome O TICKET` | outcome is one of fixed, wont-fix, duplicate, invalid, done; `--no-evidence` and `--no-changelog` exist, with `--reason` |
| `frob ticket drop ID --reason R` | `frob ticket drop TICKET --reason R` | closes as wont-fix |
| `frob ticket reopen ID --reason R` | `frob ticket reopen TICKET --reason R` | |
| `frob ticket evidence ID NODE` | `frob ticket evidence add --provider P TICKET` | providers: nextest, command, file, attestation; `--accepts N` binds an acceptance criterion |
| `frob ticket priority`, `points`, `label`, `scope`, `accept`, `set` | `frob ticket update TICKET` with `--priority`, `--points`, `--add-label`, `--add-scope`, `--add-acceptance`, `--set key=value` | |
| `frob ticket block`, `unblock` | `frob ticket link --kind blocked-by A B`, `frob ticket unlink` | v2 has 17 link kinds |
| `frob ticket set-parent`, `epic` | `frob ticket new --parent P`, `frob ticket list --parent P` | |
| `frob ticket sprint`, `milestone` | `frob cycle ...`, `frob milestone ...` | cycles and milestones are objects in the ledger, not ticket fields |
| (none) | `frob ticket comment TICKET` | new in v2; comment types: note, decision, question, answer |
| `frob check [--ticket ID] [--json] [--fix]` | `frob check [--ticket HANDLE] [--json] [--fix]` | v2 adds `--only FAMILY`, `--explain RULEID`, `--timing`, `--fail-on`; v1's `--skip STAGE` has no v2 flag |
| `frob test [--base REF] [--all]` | `frob test --base REF` or `frob test --all` | |
| `frob ack REF --reason R` | `frob ack [SYMREF or PATH] --reason R` | v2 has `--all` and `--dry-run`; v1's `--facet` and `--list` have no v2 flag |
| `frob graph why`, `affects` | `frob graph why`, `frob graph affects` | v1's `graph build` has no v2 verb |
| `frob doctor` | `frob doctor` | reports toolchain, git, cache, config and ledger health |
| `frob release stamp`, `check`, `sync` | `frob release changelog`, `status`, `bump`, `cut` | different model, see below |
| (none) | `frob init`, `config show`, `config sync`, `lease list`, `lease widen`, `schema` | new in v2 |

v1 verbs with no counterpart in 0.532.0 (none appears in v2's `frob --help` or
`frob ticket --help`): `scaffold`, `explore`, `parse`, `agent`, `worktree`,
`refactor`, `narrative`, `pool`, `profile`, `registry`, `vet`, `perf`,
`mutate`, `serve`, `sys`, `process`, `deploy`, `fleet`, `clean`, `format`,
`claude`, `natives`, `coverage`, `status`, `verify`, `sync-skills`, and the
ticket verbs `plan`, `wave`, `flow`, `sweep`, `reconcile`, `migrate`,
`renumber`, `promote`, `archive`, `restore`, `reverify`, `waive-audit`,
`scope-ack`, `anchor`, `review`, `tier`, `kind`, `component`, `tokens`,
`runs-last`, `attach`, `body`, `admin`, `fail`, `done-report`. If you depend on one, stay on v1.

Releases differ in kind. v1 derived a semver bump from the public API graph.
v2 cuts a milestone: `frob release status` reports readiness, `frob release
cut VERSION` bumps one lockstep version, compiles `CHANGELOG.md` from
`changelog.d/` fragments, commits and tags.

## What `frob init` writes

Run `frob init` in a git repository. It is safe to repeat, and
`frob init --dry-run` reports what it would change. In an empty repository it
did the following:

- `frob.toml`: created, with every knob of the `check`, `compute`,
  `directives`, `evidence`, `git`, `pm`, `release` and `tickets` tables set to
  its default and a comment above it. Reference: [config](../reference/config.md).
- `.gitignore`: adds `.frob/` (the local cache).
- `.gitattributes`: adds merge rules for `tickets/**/ticket.md`,
  `tickets/_milestones/*/milestone.md` and `tickets/_cycles/*/cycle.md`, all
  `merge=frob-ledger`.
- local git config: sets `merge.frob-ledger.driver` to a `frob merge-driver`
  command with the absolute path of the frob that ran `init`, and
  `merge.frob-ledger.name`. `--driver-command TEXT` writes a command of your
  choosing; `--fix-driver` rewrites a driver that points at a different frob.

It does not create `tickets/` or `frob.lock`. `frob ticket new --title T`
creates `tickets/` and commits the new ticket.

An existing v1 `frob.toml` is not read as is. In a test, v2 refused a v1
`frob.toml` that had a key it does not know (`default_milestone` in
`[tickets]`) with `E-CONFIG`, and `frob init` and `frob config show` failed the
same way. Move the v1 file aside, run `frob init`, then copy over the settings
you want, using `frob config show` to see the knobs.

## Move your tickets

There is no `frob migrate` verb in 0.532.0. The only path is a one-off
converter, `gob-dev import-v1-tickets`, that lives in the frob source
repository (<https://github.com/lognd/frob>) and is not published to crates.io
or PyPI. You need a checkout of the v2 source and a Rust toolchain.

```sh
# in the v2 source checkout
cargo dev import-v1-tickets --from /path/to/your-repo/tickets --to /path/to/tickets-v2
```

`--to` must be empty or absent. `--dry-run` converts and verifies in memory and
writes nothing. `--map-out FILE` writes a `T-NNNN<TAB>ulid` map and
`--report-md FILE` writes the migration report.

Then, in your repository:

1. Replace the v1 `tickets/` directory with the converted tree (the v1 files
   stay in git history).
2. Run `frob init` and `frob ticket doctor`.
3. Commit.

What it does:

- Reads `tickets/T-NNNN/ticket.md` directories; drafts and other names are skipped.
- Gives each ticket a new ULID; the v1 id is kept as an alias, so
  `frob ticket show T-0969` resolves.
- Maps state, kind and tier to type, category and outcome. In-progress becomes
  todo; dropped becomes done with outcome wont-fix.
- Carries parent, blocked-by, scope, labels, points, priority, milestone and
  component (as labels), acceptance criteria and the body.

Limits, stated plainly:

- Acceptance criteria arrive unbound (not evidenced).
- Only v1 evidence lines recorded as commands (`cmd:`) become evidence events.
  Bare pytest node ids are skipped, with a warning on stderr per id.
- Creation times are synthetic: v1 kept only a date, so event times are offsets
  from it. Real times are in git history.
- A `blocked_by` that names a ticket missing from the ledger (for example a
  draft id) is dropped, with a warning.
- Many v1 fields are dropped: worktree, branch, sprint, rank, token usage, the
  scope, body and triage audit trails, waivers and others. The full list with
  reasons is in [the v1 import report](../migration/v1-import.md).
- Only tickets move. `frob.toml`, `frob.lock`, `frob:` directives in your code,
  `invariants/`, `decisions/` and `design/` are not converted.

I ran the converter on this project's own v1 ledger (1243 tickets), put the
output in a fresh repository after `frob init`, and `frob ticket doctor`
reported 1243 tickets and no issues.

## Not verified

- That `pip install -U frob` moves a pinned-by-command install to v2: 0.532.0
  is not published yet, so no upgrade was run. The uv behaviour above was run
  against 0.531.0 only.
- That `pip install frob==0.531.0` works on your Python: the package metadata
  was read (`>=3.11`) but pip was not run on a supported interpreter.
- That v2 reads your v1 `frob.lock` or `frob:` directives, and which v1
  `frob.toml` keys v2 accepts beyond the one that failed.
- That `cargo dev import-v1-tickets` is the same invocation as running the
  built `gob-dev import-v1-tickets` binary, which is what was run.
- That the importer is present at the 0.532.0 tag of the source repository.
