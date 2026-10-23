# Upgrade from frob v1 to v2

Status: current
Owner: frob
Decisions: none
Audience: user

How-to guide (Diataxis: task). Read this if you use frob 0.531.0 or earlier,
or if you have never seen v2 and want to know what the 0.532.0 upgrade does.

frob 0.532.0 is the v2 rewrite, written in Rust. It replaces v1 on upgrade:
installing or upgrading the `frob` package after 0.531.0 gives you v2.
0.532.0 is on PyPI. The
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
  upgrades to v2 (0.532.0 is on PyPI), so keep the pin in your requirements
  file or constraints file.
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
  `merge=frob-ledger`. When `core.autocrlf` is `true` it also adds
  `tickets/** text eol=lf`, so a Windows checkout does not rewrite ledger files
  to CRLF; the init report lists it as `eol_pin`. `input`, `false` and unset
  add nothing, and a repeated run does not add it twice.
- `[evidence] attesters`: set to the git `user.email` of the repository owner
  (the identity configured where `frob init` ran). Only that identity may
  attest a criterion until you edit the list; with no `user.email` the list is
  empty and nobody may attest.
- local git config: sets `merge.frob-ledger.driver` to a `frob merge-driver`
  command with the absolute path of the frob that ran `init`, and
  `merge.frob-ledger.name`. `--driver-command TEXT` writes a command of your
  choosing; `--fix-driver` rewrites a driver that points at a different frob.

It does not create `tickets/` or `frob.lock`. `frob ticket new --title T`
creates `tickets/` and commits the new ticket.

An existing v1 `frob.toml` is not read as is. v2 refuses an unknown key
inside a table it knows with `E-CONFIG`, and `frob init` and `frob config show`
fail the same way. Move the v1 file aside, run `frob init`, then copy over the
settings you want using the mapping in [Migrate frob.toml](#migrate-frobtoml).

## Move your tickets

There is no `frob migrate` verb in 0.532.0. The only path is a one-off
converter, the `import_v1` example of `frob-evidence`, that lives in the frob source
repository (<https://github.com/lognd/frob>) and is not published to crates.io
or PyPI. You need a checkout of the v2 source and a Rust toolchain.

```sh
# in the v2 source checkout
cargo run -p frob-evidence --example import_v1 -- --from /path/to/your-repo/tickets --to /path/to/tickets-v2
```

By default every v1 ticket imports (open ones as open work); pass
`--selection FILE` to import only the open tickets that file names. Ticket files
with CRLF line endings (`core.autocrlf=true`) are read as they are. A v1 `sprint`
field becomes a `sprint:<value>` label, like `milestone` becomes `milestone:<value>`.

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
- Many v1 fields are dropped: worktree, branch, rank, token usage, the
  scope, body and triage audit trails, waivers and others. The full list with
  reasons is in [the v1 import report](../migration/v1-import.md).
- Only tickets move. `frob.toml`, `frob.lock`, `frob:` directives in your code,
  `invariants/`, `decisions/` and `design/` are not converted.

I ran the converter on this project's own v1 ledger (1243 tickets), put the
output in a fresh repository after `frob init`, and `frob ticket doctor`
reported 1243 tickets and no issues.

## Merge v2 main into a v1 branch

Use this when a long-lived branch still carries the v1 `tickets/` tree and
`main` has the converted v2 tree. A plain merge is wrong here, and not only
noisy. In the project that hit this, about 600 ticket files conflicted,
because git's rename detection paired a v1 `done-report.md` with a v2
`events/*.toml` file of similar text. Where git does not stop, it can merge a
v1 edit into an unrelated v2 event file without a conflict marker. Do not
resolve those pairs by hand.

The rule is that `main`'s `tickets/` tree wins in full. Run this on the v1
branch:

```sh
git fetch origin
git merge --no-commit --no-ff origin/main   # conflicts in tickets/ are expected
git rm -r -q -f --ignore-unmatch tickets
git checkout origin/main -- tickets
git diff --quiet origin/main HEAD -- tickets && echo "tickets/ matches main"
git commit
```

Resolve any conflicts outside `tickets/` as usual before the commit. The
`git diff --quiet` line prints the message only when `tickets/` is identical to
`main`'s. Afterwards run `frob ticket doctor`.

Notes:

- `git merge -X no-renames origin/main` stops the wrong pairing, but it does
  not make `tickets/` conflict-free. A v1 ticket file that the branch changed
  and `main` deleted becomes a modify/delete conflict. Use it if you want git to
  merge the code unattended, then run the `git rm` and `git checkout` lines
  above for `tickets/`. To make it the default for one repository, run
  `git config merge.renames false`.
- No ticket data is lost. The v1 tree stays in the history of the branch, and
  `main` already holds every ticket it imported.
- Tickets created on the v1 branch after the import do not exist in `main`.
  Take them from the branch before merging: run the converter on the v1 tree
  (`git show` of the branch or a checkout of it) as described in [Move your
  tickets](#move-your-tickets), and add the result to `main`. Taking `main`'s
  tree drops them from the working tree only.
- The `merge=frob-ledger` driver from `frob init` applies to v2 ticket files
  only. It does not help with the v1 files.
- The importer report, [the v1 import report](../migration/v1-import.md),
  links back to this recipe.

## Migrate frob.toml

There is no migrate command. The owner decision of 2026-10-09 is that you move
`frob.toml` by hand with this table. Start from the file `frob init` wrote.
v2 ignores a whole top-level table it has no schema for, and refuses an unknown
key in a table it has (as `default_milestone` in `[tickets]` and
`dev_version_bump` in `[release]`). Delete a removed key, or the run stops with
`E-CONFIG`.

Every v1 key is below. "Removed" means v2 has no knob and you delete the key.

| v1 key | v2 key | Why |
|---|---|---|
| `min_frob_version` | removed | v2 has no minimum-version pin in `frob.toml`. |
| `check_base` | `[check] base` | Same meaning: the ref a `--ticket` run diffs against. |
| `[dup]` `enforce`, `threshold`, `region_kernel`, `native_rungs` | removed | The `DUP` rules run with fixed settings; none is a knob. |
| `[graph]` `exclude` | `[check] exclude` | Globs of paths no rule inspects. |
| `[arch]` `max_function_lines`, `max_class_methods`, `max_local_imports`, `max_nesting_depth`, `max_file_lines`, `lcom4_min_methods`, `lcom4_min_field_using_methods`, `god_module_min_exports`, `god_module_min_clusters`, `mixed_concern_min_decision_points` | removed | v2 does not keep the v1 architecture-metric thresholds; its size rules use `[check] size_cap` only for skipping large files. |
| `[arch.layering.layers]`, `[arch.layering.allow]` | `[invariants] forbid_imports` | v2 states forbidden imports, each with a `reason`, not allowed layers. Rewrite each disallowed edge as a `forbid_imports` entry. |
| `[[docblocks.commands]]` `prog`, `parser`, `config`, `forwarded` | removed | The v1 CLI doc-block check has no v2 counterpart; reference pages are generated. |
| `[[refs.entrypoint]]` `path`, `reason` | removed | v2 has no entry-point list for dead-symbol checks. |
| `[gates.severity]` | `[packs.severity]` | v2 overrides severity by atom, then rule. The keys are not the same shape, so rewrite them. |
| `[gates.ratchet]` `rules` | removed | v2 has no ratchet table; `[check] fail_on` sets the failing severity. |
| `[testing]` coverage floors (`unit_branch_cov`, `module_line_cov`, `system_line_cov`) | `[[coverage.threshold]]` | Minimums per scope, read from an lcov report (`[coverage] report`). |
| `[testing]` case counts (`min_unit_cases`, `min_integration`) | removed | v2 binds tests to tickets with evidence, not by count. |
| `[[test.runner]]` `language`, `command`, `all_command`, `cwd`, `collector`, `timeout_s` | `[tests] python`, or `[evidence]` providers | v2 runs tests through evidence providers; `[tests] python` picks the interpreter for pytest. |
| `[[native]]` `name`, `build_cmd`, `language` | removed | v2 does not build native extensions for you. |
| `[profile]` `profile`, `override_ratchet` | removed | Profiles and the ratchet are gone. |
| `[profile]` `backpressure_max_depth`, `backpressure_max_age_s`, `rapid_soft_warn_depth`, `rapid_soft_warn_age_s`, `stale_archive_warn`, `stale_archive_error` | `[pm.wip]` and `[pm.max_age_days]` | Flow limits live in the `[pm]` tables, set per class. |
| `[tickets] default_milestone` | removed | Refused with `E-CONFIG`. Milestones are tickets of their own; use `frob milestone add`. |
| `[worktree]` | `[worktree] dir` | Parent directory of ticket worktrees. |
| `[strata]` `design_dir`, scope and capability maps | removed | The strata model is replaced by `[grimble]` and `[packs]`. |
| `[vet]`, `[vet.allow]`, `[vet.detectors]` | removed | Vet is not a v2 verb. Use `frob:accept` for a permanent exception. |
| `[clean]` | `[gc]` | `frob gc` replaces the clean sweep. |
| `[perf]` sketch store, sampler, redundancy keys | `[perf] budget_ms`, `enforce` | v2 keeps only a time budget for its own rules. |
| `[fuzz] enforce` | removed | No fuzz gate. |
| `[sys]`, `[ty] target_platforms` | removed | No counterpart. |
| `[release] dev_version_bump`, `dev_version_major_ack` | removed | Refused with `E-CONFIG`. See `[release]` in the [config reference](../reference/config.md). |
| `[*_schema] known_keys` (ten tables) | removed | v1 schema-of-the-schema checks; v2 checks keys itself. |

The v1 table `[project]` and `[tool]` belong to Python packaging, not frob.
Leave them in `pyproject.toml`. The current knob list is in the
[config reference](../reference/config.md); run `frob config show` after
editing.

## Migrate directives by hand

v1 `frob:` directives in your code are not converted. Two rewrites are needed.

`frob:waive` becomes one of two directives, chosen by whether the waiver
carries a ticket:

| v1 | v2 |
|---|---|
| `frob:waive RULE reason="text"` (permanent) | `frob:accept RULE because="text"` |
| `frob:debt RULE reason="text" ticket="T-0160"` or a waiver whose reason names a ticket | `frob:defer RULE because="text" ticket=<full ULID>` |

Rules:

- `reason=` is renamed `because=`, and it is required in v2.
- A permanent exception is `frob:accept`. It takes an optional `until=`.
- A tracked gap is `frob:defer`. `ticket=` is required and must be the full
  26-character ULID, not `T-0160`. Look the ULID up with
  `frob ticket show T-0160` after the import, because the v1 id is an alias.
- The rule id itself may have changed. Check it in the
  [rule reference](../reference/rules/); a rule v2 does not have means the
  directive can be deleted.
- `frob:ticket T-0160` becomes `frob:ticket <full ULID>` the same way.

The `frob:tests` direction flips. In v1 the directive sat on the code symbol
and its target was a test id (`path::Class.method`). In v2 it sits on the test
and its target is the symbol it covers (a symref). To migrate, move each line
from the code to the test it names, and swap the target for the code symbol.
The optional `kind=` argument keeps its meaning.

## Not verified

- That `pip install -U frob` moves a pinned-by-command install to v2: no
  upgrade was run here, although 0.532.0 is on PyPI. The uv behaviour above was
  run against 0.531.0 only.
- That `pip install frob==0.531.0` works on your Python: the package metadata
  was read (`>=3.11`) but pip was not run on a supported interpreter.
- That v2 reads your v1 `frob.lock` or v1 `frob:` directives: it does not
  convert them, so migrate by hand as above.
- That each mapped v2 key behaves like its v1 counterpart. The mapping says
  which v2 key is closest; it was checked against the config reference, and
  only the unknown-key refusal was run against the release binary.
- The merge recipe was run on a small test repository, not on a 600-conflict
  history.
- That the importer is present at the 0.532.0 tag of the source repository.
