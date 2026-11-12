# Architecture: workspace, git, paths and time

Status: current
Owner: gob
Decisions: D86, D93
Audience: contributor

How the workspace is built and run (part 1), how it reaches git and GitHub (part 2), and the two typed
disciplines that run from type to lint (part 3: paths, then time). Merged from the former
architecture.md, architecture.md, architecture.md and architecture.md.

## 1. Architecture

Provenance: written under T-0001 (a v1-format id that migrates with an alias).
Inputs: notes/research/rust-ecosystem.md, notes/v1/ops-and-integrations.md
(telemetry), notes/v1/gates-and-rules.md.

### 1.1 Shape and layering

The workspace has three binaries (`frob`, `grimble`, `crunk`) built from one Cargo
workspace with strict downward dependencies. The crate list is the capability map in
[charter.md](charter.md) section 4.2 (crates under `crates/` are the
source of truth); the early tree sketch is kept in
[milestones.md](../../history/milestones.md). `gob-db` and the
`frob-hook`, `frob-explore`, `frob-fleet`, `frob-gh` and
`frob-serve` crates named below are planned and do not exist yet; the
`frob` binary crate holds the CLI today (`frob-cli` is its crates.io publish name).

`gob-dev` is the one substrate crate that is a binary: the `cargo dev`
generator (ruff's ruff_dev pattern), never shipped. Layering, enforced
by a repo-internal rule over Cargo metadata and by the dependency graph:
`gob-*` depends only on `gob-*`; product crates depend on `gob-*` and
their own product; products never depend on each other, with the one
stated exception that the `frob` binary with feature `bundle` links
`grimble-check` (which drives the shared `gob-check` pipeline) and crunk's check crate to run them in-process
(docs/design/shared/charter.md section 4.6). Within the substrate the real order is:
`gob-text` and `gob-macros` at the bottom (neither depends on another
workspace crate); then `gob-config`, `gob-walk`, `gob-cache` and
`gob-languages` (text); `gob-ir` (the universal model: terms, scope
graph, canonical facet stream, queries, Kleene evaluator; depends on
`gob-text` and `gob-languages` only; Milestone 2 or later (D36));
`gob-rules` (macros, text and, from milestone 2, the answer lattice
from `gob-ir`); `gob-symbols` (the adapters that produce U terms;
languages, ir, cache, walk); `gob-directives` (languages, rules,
symbols); then `gob-git`, `gob-exec`, `gob-log`, `gob-lock`,
`gob-diagnostics`, `gob-fix`, `gob-pattern`, `gob-check`; and
`gob-serve`, `gob-mdtest` and `gob-db` (salsa, Milestone 2 or later
(D36)) on top. The full chain is `gob-languages` < `gob-ir` <
`gob-symbols` < `gob-directives` < the frob and grimble crates; frob
links `gob-ir` (D56, superseding the D31 claim that frob builds
without it).

### 1.2 Data flow of one invocation

1. `main` builds `Cli` (clap derive via `gob-cli`), installs tracing,
   opens the repository once through `gob-git` (gix, no subprocess),
   opens the repository-shared cache (`$XDG_CACHE_HOME/frob/cache/<repo-id>/frob/cache.sqlite`, rows MAC'd under the machine key (security.md 2.2)), records invocation start (telemetry spans the WHOLE
   process this time; v1 timed only dispatch and missed test and graph
   entirely).
2. The command handler asks the snapshot layer for what it needs.
   Inputs are files (content by blake3), config, git facts (HEAD, diff
   vs base), ticket files. Derived data: parse artifacts, symbols,
   directives, imports and call graph, ticket index, snapshot joins, and
   rule findings. Milestone 1 computes these with plain rayon functions
   over per-file memo tables; from milestone 2 the same keys back a
   salsa `Db` (`gob-db`, Milestone 2 or later (D36)).
3. Results that are expensive and stable are persisted to the SQLite
   file of this repository, shared by its worktrees (`$XDG_CACHE_HOME/frob/cache/<repo-id>/frob/cache.sqlite`, rows MAC'd under the machine key (security.md 2.2)): parse artifacts keyed by
   (content blake3, adapter id, grammar version, schema version, and
   from milestone 2 a digest of the `[compute]` config; the scope graph
   is a repo-scope artifact keyed by the graph digest, code-model.md
   section 1.8); per-file findings keyed
   by (file digest, rule id, rule version, side-input digest); repo-scope
   findings keyed additionally by a graph digest. Persistence happens
   from the command layer after queries return, never inside a query;
   writes are best-effort with a `busy_timeout`, and a failed write is a
   logged cache miss, never an error. A long-lived `frob serve` keeps
   the same data warm in memory (Milestone 2 or later (D36)).
   Files the walk includes but the analysis cannot read are never
   silent (`READ001`). Every such file (content that is not UTF-8, a
   permission or other read failure, a file over `[check] size_cap`)
   becomes one required Unresolved finding naming the path and the reason,
   so the default `fail_on_unresolved = "required"` gate fails, and the
   `fidelity.skipped` section of the report counts them by reason
   (`encoding`, `permission`, `io`, `size`). Unreadable files are in no
   language row and are not "examined". The `--ticket` fold of findings
   outside the diff into counts never hides them: a required finding
   always prints in full. Declared binary or generated files are
   excluded, not reported, by two routes only: a `[check] exclude` glob
   keeps the file out of the walk, so it is never read, hashed or
   reported; and an opaque file with a binary extension or a NUL in its
   head is `NotApplicable` for the text rules, and when it is over
   `size_cap` it is not reported either. A file claimed by an adapter
   (`.md`, `.rs`, `.toml`) that cannot be decoded is always reported;
   exclude it explicitly if it is generated.
   Generated report directories are skipped by default (gob-walk
   `GENERATED_DIRS`, defined once and shared by every product walk):
   `coverage/` holding `lcov-report`, `prettify.js` or `base.css`, and
   `lcov-report/`, `htmlcov/`, `playwright-report/` each holding
   `index.html`, at any depth. The marker file keeps a hand-written
   `src/coverage/` walked; tracked and gitignored report directories are
   treated alike. A `[check] exclude` entry `"!coverage/"` opts that
   default back in (the leading `!` removes the default rule of that
   name; it is never passed to the glob matcher).
4. Render through `gob-diagnostics`; every finding carries a remedy
   string generated from the rule's `fix_title` or `remedy` doc section.
5. Exit code per the table in docs/design/shared/cli-contract.md section 2: 0 ok (domain state such
   as "findings exist" is not a failure), 1 negative domain answer when
   requested, 2 usage, 3 refused by a guard with remedy and
   `retryable`, 4 internal error.

Performance budget (from v1 telemetry: `ticket show` median 2.7s,
`check` median 220s, half of all invocations were land status polls):

| Operation | v2 target |
|---|---|
| any read-only ticket verb | < 50 ms |
| any ticket mutation | < 100 ms |
| warm scoped check | < 1 s |
| warm full check, 100k lines | < 2 s |
| cold full parse, 100k lines | parse-bound, parallel |
| land, excluding tests | < 5 s |

"Warm" means a fresh process with a populated per-worktree `.frob/`
cache; it does not mean a daemon. External tool stages (`[[check.tool]]`)
and the documentation gates are outside the 2 s budget and are reported
as separate stages in `--timing`. `ticket close` and `land` run
evidence, measurers and checks and are outside the 100 ms mutation
budget; they obey the timeout contract of docs/design/shared/cli-contract.md section 3. The bench
crate measures the fresh-process case.

### 1.3 Storage

| Artifact | Location | Tracked |
|---|---|---|
| tickets | `<epic-slug>/<slug>.md` on the `frob-tickets` branch (TOML frontmatter + markdown) | yes |
| ticket events (comments are events) | `.events/<ulid>/<ulid>.toml` on the `frob-tickets` branch | yes |
| non-ticket events (budget raises, audits, reviews of exceptions) | `events/<ulid>.toml` at the repo root | yes |
| acks | `frob.lock`, `grimble.lock` (one lock file per product, `gob-lock`) | yes |
| exceptions | `exceptions.toml` (one array per product: `[[frob.exception]]`, `[[grimble.exception]]`, `[[crunk.exception]]`; the accept digest lives in the lock, docs/design/shared/rules.md section 10.2) | yes |
| ratchet pools | `frob-ratchet.lock.json`, `grimble-ratchet.lock.json` | yes |
| quarantine (Milestone 2 or later (D36)) | `frob-quarantine.json` | yes |
| design model | `design/*.grmb` (grimble) | yes |
| invariants, decisions | `invariants/INV-*.md`, `docs/decisions/*.md` | yes |
| config | `frob.toml`, `grimble.toml`, `crunk.toml` (one per product) | yes |
| pack drift-lock | `grimble.packs.lock` (one per repository, written only by `grimble packs update`; docs/design/shared/packs-and-plugins.md section 12.4) | yes |
| leases | `<common_dir>/frob/leases/<ulid>.toml` plus one `<common_dir>/frob/leases.lock`; single clone, shared by its worktrees | no |
| local evidence artifacts | `.git/frob/artifacts/` (non-authoritative; a missing blob reads as Unmeasured; old unreferenced blobs are collected) | no |
| garbage-collection stamp | `<common_dir>/frob/gc.json` (last pass, throttle) | no |
| cache, index, telemetry | `.frob/` per worktree: `tickets.sqlite` (frob-ledger index, keyed by the tickets subtree id, not the whole tree), plus `cache.sqlite` (gob-cache) once per repository under the per-user cache directory (`$XDG_CACHE_HOME/frob/cache/<repo-id>/`, MAC'd rows; supersedes the in-tree placement of D30/D38) | no, delete-safe |

Nothing authoritative under `.frob/`. Deleting it costs one cold parse.
The deliberate non-git state is exactly: leases (loss means locks
vanish; no data is lost), local evidence artifacts (loss degrades
verdicts to Unmeasured, which is never a finding on a terminal ticket),
and the per-worktree cache. Plan tokens are digests recomputed at apply
and stored nowhere; there is no job store in milestone 1.

#### 1.3.1 Garbage collection (~BZXZK29)

frob owns local state and the build output of the checkouts it manages, so
it also keeps them under budget; goway owns its remote hosts and their own
collection. There is no collection verb. An opportunistic pass runs inside
verbs that already run often and are about to need disk: `frob work` (before
a new worktree builds) and `frob land` (after the worktree is removed), and
unthrottled from `frob doctor --fix`. `frob doctor` reports the stamp
only; the dry-run plan (what a pass would reclaim) is opt-in via `--gc-plan`. A stamp `<common_dir>/frob/gc.json` throttles automatic passes to
one per `[gc] interval_secs` (default 1 h) and records the last pass for
`doctor`; free space below `[gc] guard_min_free_gb` (default 20 GiB, 0 turns it
off) overrides the interval. The pass is bounded by `[gc] time_limit_secs`,
never fails the verb (every problem is a warning in the verb's output and a log
line), and logs a summary at info.

What is collected, in order, each category with its own knob:

| Category | Rule |
|---|---|
| worktrees | finished ticket worktrees (frob/tickets.md, "Worktree garbage collection"); never one with uncommitted changes |
| `land-base` | abandoned ratchet base checkouts `<common_dir>/frob/land-base-*` older than an hour (a land that crashed; a running land refreshes its own) |
| build | per checkout (the primary and the live worktrees), through a `BuildAdapter` (Cargo first, `target/<profile>`): incremental directories unused for `incremental_max_age_secs` (6 h) go regardless of size; then the oldest artifacts (a compilation unit's `deps/` files, `build/` script directories) go until the target dir is under `target_budget_gb` (30 GiB). Anything within `keep_recent_secs` (1 h) of the newest artifact belongs to the latest build and stays, as do `keep_binaries` (`frob`, `grimble`) |
| caches | an allowlist under each checkout's `.frob/` and under the shared `<git common dir>/frob/` (`cache/<product>/cache.sqlite` with its companions and `land-base/*.json`), least recently modified first over `cache_budget_mb`; a cache touched in the last hour may be open and stays; locks, the ticket index, journals and repair state are never touched |
| artifacts | `<common_dir>/frob/artifacts` blobs (named by 64-hex digest) older than `artifact_retention_days` that no open ticket's events mention; if the open tickets' events cannot be read nothing is removed |

Safety is structural. Every path goes through a `Jail` before anything touches
it: the roots are the target dirs of the checkouts, frob's own state under the
common dir (`<common_dir>/frob`), a checkout's `.frob/`, and the worktree
parent; containment is decided on path components (never string prefixes, so
`target-old` is not inside `target`), a path with `..` or one that is itself a
symlink is refused, a symlinked parent canonicalises outside the roots and is
refused, and a root is never removed itself. Tree removal unlinks a symlink
inside the tree instead of following it. Worktrees are additionally removed
only through `git worktree remove` without `--force`. A new ecosystem adds a
`BuildAdapter` (output directories, removable units); the eviction plan over
the units is shared.

### 1.4 Errors

Library crates return `Result<T, E>` with per-crate error sets. The
house idiom is typani's ErrorSet; in Rust that is `error_set!` (crate
`error_set`), trialled first in `frob-ledger` (decided 2026-10-02;
notes/research/rust-ecosystem.md flags its miette interop as unverified); if its miette interop
disappoints, fall back to `thiserror` enums with a shared `Code` trait.
Trial outcome (milestone 1): `error_set` is kept in `frob-ledger`; the
other crates written so far (for example `gob-exec`) use `thiserror`
enums.
Rules for every crate:

- Every error variant has a stable code (`E-LEDGER-NOTFOUND`) and a
  remedy string; `gob-diagnostics` renders both. Codes are collected by
  `cargo dev gen` into the generated errors page (documentation.md
  section 1.3).
- Panics are programmer bugs. `unwrap` is denied by clippy config
  outside tests; `expect` requires a message naming the invariant.
- No defensive handling of impossible states: unreachable arms use
  `unreachable!("why")` and are covered by a test if reachable.
- Guards (refusals such as "dirty root", "lease held") are not errors;
  they are a `Refusal` type with exit code 3 and a remedy, so agents can
  distinguish "retry after X" from "bug".

### 1.5 Logging and telemetry

`tracing` everywhere. `main` installs a subscriber with: a human layer
to stderr honoring `-v/-vv` and `FROB_LOG` (env-filter), a JSON layer
appended to `.frob/log.jsonl` when `[telemetry] file = true`, and a span
per command and per rule. Every state change (ticket transition, lease
take, ack, land step, cache write) is an `info!` event with structured
fields; every boundary (git call, subprocess, network) is a span with
duration; every error path logs at the point of origin once. `frob
--timing` prints the span tree for the invocation. Telemetry records
`(command, args shape, duration from process start, exit, repo hash)`
per invocation in `.frob/telemetry.jsonl`; `frob stats` mines it.

Redaction: `gob-log` owns one redactor (token-shaped strings, URLs with
credentials, values of environment variables named like secrets).
`gob-exec` applies it to every captured command output before that
output is stored as evidence or logged, and telemetry applies it to
the args shape. A TICK rule scans the ledger event files (`.events/*/*.toml`) for the
same patterns so a transcript that bypassed capture is still caught.

No `println!` outside the renderer crate; the workspace denies clippy
`print_stdout`, `print_stderr` and `dbg_macro` (`Cargo.toml`), with tests exempt
in `clippy.toml` and build scripts, benches and fake CLI fixtures allowing them
at crate level with a stated reason.

### 1.6 Configuration

Each product has one config file (`frob.toml`, `grimble.toml`,
`crunk.toml`), each one serde model with `deny_unknown_fields` (kills
the eleven v1 `*SCHEMA001` gates), loaded by `gob-config`. Each table is a struct with
`#[derive(ConfigTable)]` which emits the JSON schema fragment and the
generated config reference page (notes/research/documentation.md section 3) from doc
comments (uv's OptionsMetadata pattern). As built (`gob-config`): the derive-registered inventory stores each
table's describe function rather than a value; `load` layers defaults,
file and overrides with per-key provenance and rejects unknown keys with
a did-you-mean; table paths may be dotted (`tickets.lease`); `check`
returns a `Result` so an unreadable file is not silently clean; and each
`FieldDescription` carries a per-field JSON schema. Layering: workspace file, then per-crate or per-dir
`frob.toml` overrides (Combine derive), then CLI flags. `frob config
show --effective` prints the merged result with provenance.

One read, one parser (audit M13): `ConfigDocument::read` reads and parses the file once and `ConfigDocument::table` loads each table from that parse, so `FrobConfig::load` touches the disk once (`gob_config::file_reads` is the counter the tests assert on). The `[tickets]` and `[git]` tables, their knob enums and the `LedgerConfig` they imply live in `frob-ledger::config`, the only parser of those tables; `frob-cli` re-exports them.

Config inventory. This table is the one place that lists every knob;
"materialized" means `frob init` writes it with its default and CFG001
flags its absence. Defaults are the initial values proposed by this
design.

In code, "materialized" is carried by the `enforcement` marker on a field (only enforcement fields are written by `frob init`); `materialize` on a table is a declaration that its enforcement fields are written.

Rows marked (M1) exist in code at milestone 1 and match the `ConfigTable`
structs of crates/frob/src/config.rs and the sibling crates' `config.rs`
files exactly (the generated docs/reference/config/frob.md is the live copy);
the other rows are the design for Milestone 2 or later (D36) and are not
yet read by any crate. Every table is under `deny_unknown_fields`.

| Key | Product file | Materialized | Default | Owning crate |
|---|---|---|---|---|
| `[tickets] ref` (M1) | frob.toml | yes | `"refs/heads/main"` | frob (config), frob-ledger |
| `[tickets] ref_mode` (M1) | frob.toml | yes | `"trunk"` (or `"branch"`) | frob (config), frob-ledger |
| `[tickets] branch` (~BAD33TS) | frob.toml | yes | `"frob-tickets"` | frob (config, `ticket branch init`), frob-ledger |
| `[tickets] dir` (M1) | frob.toml | no | `"tickets"` | frob (config), frob-ledger |
| `[tickets] handle_min_len` (M1) | frob.toml | no | 7 | frob (config), frob-ledger |
| `[tickets] actor` (M1) | frob.toml | no | empty (git `user.name`) | frob (config), frob-ledger |
| `[check] fail_on` (M1) | frob.toml | yes | `"error"` (`"none"` never fails) | frob (config), gob-diagnostics |
| `[check] exclude` (M1) | frob.toml | no | empty | frob (config) |
| `[check] size_cap` (M1) | frob.toml | no | 4194304 bytes | frob (config) |
| `[git] cas_retries` (M1) | frob.toml | yes | 5 | frob (config), gob-git |
| `[cache] busy_timeout_ms` (M1) | frob.toml | no (performance only) | 500 | frob (config), gob-cache |
| `[lease] ttl_secs` (M1) | frob.toml | no | 7200 | frob-lease |
| `[lease] lock_timeout_ms` (M1) | frob.toml | no | 5000 | frob-lease |
| `[lease] shared_files` (M1) | frob.toml | no | empty (append-shared files such as `Cargo.lock`) | frob-lease |
| `[worktree] dir` (M1) | frob.toml | no | `"../{repo}-wt"` | frob-worktree |
| `[gc]` (~BZXZK29: `enabled`, `interval_secs`, `time_limit_secs`, `guard_min_free_gb`, `incremental_max_age_secs`, `target_budget_gb`, `keep_recent_secs`, `keep_binaries`, `cache_budget_mb`, `artifact_retention_days`, `worktrees`) | frob.toml | no | on; 1 h interval, 30 s bound, 20 GiB guard, 6 h incremental age, 30 GiB per-checkout budget (see Garbage collection, section 1.3) | frob-worktree |
| `[evidence] allowed_tools` (M1) | frob.toml | no | `["cargo", "git", "pytest"]` | frob-evidence |
| `[evidence] inline_max_bytes` (M1) | frob.toml | no | 16384 | frob-evidence |
| `[evidence] store` (M1) | frob.toml | no | `"dir:.git/frob/artifacts"` | frob-evidence |
| `[evidence] timeout_secs` (M1) | frob.toml | no | 1800 | frob-evidence |
| `[evidence] nextest_profile` (M1) | frob.toml | no | empty (nextest's own default) | frob-evidence |
| `[invariants] forbid_imports` (M1) | frob.toml | no | empty (entries of `from`, `to`, `reason`) | frob-obligations |
| `[check] fail_on_unresolved` | frob.toml | yes | `"required"` (`"never"` or `"all"`; the one gate mechanism, docs/design/shared/cli-contract.md section 2; today gob-diagnostics skips Unresolved, Milestone 2 item 1) | frob (config), gob-diagnostics |
| `[check] require_siblings` | frob.toml | yes | true (a configured sibling that is absent or incompatible is a required Unresolved) | frob-check |
| `[check] sibling_timeout_secs` | frob.toml | yes | 120 (wall-clock bound of one sibling `check --json` run; expiry is a required Unresolved `SIB001` with reason `timeout`; docs/design/shared/sibling-contract.md section 7) | frob-check |
| `[check] ticket_hops` | frob.toml | yes | 1 | frob-check |
| `[[check.tool]]` | frob.toml | no (opt-in list) | none | frob-check |
| `[land] verify` | frob.toml | yes | `"sync"` (`"ci"` is Milestone 2 or later (D36)) | frob-land |
| `frob land --push` (flag, not a config key) | CLI flag | n/a | off | frob-land; pushes the base branch during landing, docs/design/frob/tickets.md section 10 |
| `[git] run_hooks` | frob.toml | yes | false | gob-git |
| `[tickets] prefix` | frob.toml | no (display only) | empty | frob-ledger |
| `[tickets] mega_glob_files` | frob.toml | yes | 500 | frob-lease |
| `[tickets.guards] close` | frob.toml | yes | has_evidence, no_open_blockers, children_terminal, lease_free | frob-ledger |
| `[tickets.archive] done_after_days` | frob.toml | yes | 0 (off) | frob-ledger |
| `[tickets.custom_fields]` | frob.toml | no (registry) | none | frob-ledger |
| `[[component]]`, labels, `[[triage.rule]]`, `[[query]]`, `[[agent]]` | frob.toml | no (registries) | none | frob-ledger |
| `[directives] namespaces` | frob.toml | yes | `["frob", "grimble", "crunk"]` (a ConfigTable, gob-directives `DirectivesConfig`); frob-check, frob-ack and frob-obligations still scan with `ScanConfig::default()` (frob only) until grimble and crunk register verbs | gob-directives |
| `[compute] public_signatures` | frob.toml (the one home; read by every product, see below) | yes | `"warn-unresolved"` (`"required"` makes an absent annotation a required Unresolved) | gob-ir |
| `[compute] effects` | frob.toml | yes | `"warn-unresolved"` | gob-ir |
| `[compute] dynamic_calls` | frob.toml | yes | `"warn-unresolved"` | gob-ir |
| `[compute] expansion_steps` | frob.toml | yes | 1000 (the macro and template expansion step budget) | gob-ir |
| `[compute] normalization` | frob.toml | yes | `"warn-unresolved"` | gob-ir |
| `[compute] notebook_order` | frob.toml | yes | `"warn-unresolved"` | gob-ir |
| `[neat] max_params` | grimble.toml | yes | 5 | grimble-lints |
| `[neat] max_depth` | grimble.toml | yes | 3 | grimble-lints |
| `[neat] raw_loop_statements` | grimble.toml | yes | 3 | grimble-lints |
| `[neat] hook_statements` | grimble.toml | yes | 3 | grimble-lints |
| `[neat] require_effects` | grimble.toml | yes | false (candidate to default on for the public surface of this repository, docs/design/grimble/rule-families.md section 5) | grimble-lints |
| `[neat.effects]` vocabulary tables (clock, rng, env, fs, net, stdio, exit per language) | grimble.toml | no (registry; defaults generated for Rust, Python, TypeScript, Go from the gob-ir vocabulary) | generated | grimble-lints |
| `[ci] allow_tag_pins_for` | grimble.toml | yes | empty (verified publishers allowed to tag-pin) | grimble-ci |
| `[ci] max_timeout` | grimble.toml | yes | 30 (minutes; `timeout-minutes` ceiling) | grimble-ci |
| `[ci] contexts` | grimble.toml | yes | the attacker-controlled context set of docs/design/grimble/rule-families.md section 5 | grimble-ci |
| `[ci] registries` | grimble.toml | no (registry) | the publish-step vocabulary of docs/design/grimble/rule-families.md section 5 | grimble-ci |
| `[ci] max_age_days` | grimble.toml | yes | 365 | grimble-ci |
| `[pm] strict`, `stories_required` | frob.toml | yes | false, true | frob-pm |
| `[pm] max_story_points`, `max_chore_points` | frob.toml | yes | 8, 2 | frob-pm |
| `[pm] max_objective_share` | frob.toml | yes | 0.4 | frob-pm |
| `[pm.max_age_days]` (`in_progress`, `ready`) | frob.toml | yes | 3, 30 (0 is off); PM008 fires past the limit for the days since the ticket entered its category | frob-pm |
| `[pm] capacity_k`, `capacity_points`, `min_history` | frob.toml | yes | 0.5, unset, 3 | frob-pm |
| `[pm] sprint_gate` | frob.toml | yes | true; with a cycle active, `work` and `start` refuse a ticket outside it with `E-PM-NOT-IN-CYCLE` (expedite exempt, `--unplanned --reason` assigns it as an over-commit) | frob-pm, frob-worktree |
| `[pm] max_duplicate_objective_text` | frob.toml | yes | 3 | frob-pm |
| `[pm] measurer_timeout_secs` | frob.toml | yes | 600 | frob-pm |
| `[pm.wip] in_progress_per_identity` | frob.toml | yes | 1 (0 is off); the one per-holder limit, applied by the lease store | frob-pm, frob-lease |
| `[pm.wip] in_progress` | frob.toml | yes | 2 (0 is off); `work` and `start` refuse past it with `E-WIP-REPO` | frob-pm, frob-worktree |
| `[pm.ready]`, `[pm.done]`, `[pm.personas]`, `[pm.attributes]`, `[pm.metrics]` | frob.toml | yes (ready, done), no (registries) | pm-and-releases.md | frob-pm |
| `[exceptions] hotfix_days` | frob.toml | yes | 14 | gob-rules |
| `[exceptions] max_defers_per_component`, `max_defer_age_days`, `max_hotfixes_open` | frob.toml | yes | 25, 90, 5 | gob-rules |
| `[exceptions] max_accepts_per_rule_per_file`, `max_duplicate_reasons` | frob.toml | yes | 3, 3 | gob-rules |
| `[exceptions] reattest_warn_days` | frob.toml | yes | 14 | gob-rules |
| `[exceptions] owners` | frob.toml | yes | the identity running `frob init` | gob-rules |
| `[rules.<id>]` severity overrides | each product file | no (only when it differs) | rule default | gob-rules |
| `[[policy]]` (tickets, docs) | frob.toml | no | none | frob-obligations |
| `[perf] threads`, `jobs` | frob.toml | no (performance only) | physical cores | gob-exec |
| `[telemetry] file` | frob.toml | no (logging only) | true | gob-log |
| `[notify] webhook` (Milestone 2 or later (D36)) | frob.toml | no | unset | frob-serve |
| `[grimble] strict`, `modeled`, `packs` | grimble.toml | yes, yes, no | false, empty, empty | grimble-check |
| `[packs] enabled` | grimble.toml | yes | the three built-ins of packs-and-plugins.md 8 (`grimble/core-effects`, `grimble/ci-github`, `grimble/rust-ecosystem`); a pack not listed is off and a model naming it is MDL009 | grimble-capabilities |
| `[packs] lock` | grimble.toml | yes | `"grimble.packs.lock"` (path of the drift-lock, one per repository; packs-and-plugins.md 3.6 and 4) | grimble-capabilities |
| `[[packs.external]]` | grimble.toml | no | none (url plus digest per external pack, vendored; packs-and-plugins.md 3.4) | grimble-capabilities |
| `[packs.severity]` | grimble.toml | no (only when it differs) | empty (repository override per atom and rule, wins over the pack; equal to the pack value is PACK008; packs-and-plugins.md 3.6 and 5) | grimble-capabilities |
| `[neat.effects.exclude.<lang>]` | grimble.toml | no | empty (names removed from the effect vocabulary, each with a `because`; packs-and-plugins.md 3.6) | grimble-capabilities |
| `[[policy]]`, `rules/*.grl.toml` (code) | grimble.toml and next to it | no | none | grimble-lints |
| crunk tables | crunk.toml | per notes/v1/crunk.md section 4 | per crunk | crunk crates |

`[compute]` is a substrate table with one home: `frob.toml`, read
identically by every product (a standalone grimble with no `frob.toml`
reads the same table from `grimble.toml`; when both files exist,
declaring it in `grimble.toml` is a CFG finding). Sibling `--json`
carries the compute-config digest and frob treats a mismatch as an
incompatible sibling (a required Unresolved, docs/design/shared/cli-contract.md section 2), so two
products never build different U terms for one file.

The `[tickets]` and `[git]` tables are validated in the `frob` binary;
frob-ledger reads just the keys it needs and ignores the rest, because
the binary depends on the crate. The ledger reads the `[tickets]` keys
without the alias folding that `[lease] shared_files` receives.

Local-only config (owner request, ~2GXRW72). Anything private cannot live in `frob.toml`, because a committed
list of private terms publishes them. Redaction rules are read from two local files and merged (user first): the
user config `<platform config dir>/frob/privacy.toml` (`XDG_CONFIG_HOME`, else `APPDATA` on Windows, `~/Library/Application Support`
on macOS, `~/.config`) and `<git common dir>/frob/privacy.toml`, next to the check cache (`frob/cache/<product>/`). Both hold
`[[rule]]` tables of `pattern`, `replace`, `regex = false`, `case_sensitive = true`. Nothing writes either file into a work
tree; `frob init` and `frob doctor` log their locations and never create them; a malformed file makes writes refuse (fail closed). The locations
are resolved by `gob-config` (`user_file`, `repo_file`); the engine is `frob-ledger::redact` (frob/tickets.md section 6).

Environment variables never change an enforcement outcome (the user config location above follows the platform
convention and only selects which local rule files exist). Only two
exist: `FROB_LOG` (log filter) and `FROB_AGENT` (actor label, also
`--actor`). Every other behaviour switch is a flag or a knob above.

No invisible variables (owner rule, 2026-10-02): a knob that changes
enforcement (PM thresholds, exception budgets, strictness flags,
capacity formula constants, hotfix days) is declared with
the `enforcement` marker on a field of a `#[config(materialize)]`
table (`ConfigTable` derive). `frob init` writes
every such knob with its default value and its doc comment into the
config file; `frob config sync` adds knobs introduced by an upgrade;
CFG001 is an Error when a materialized knob is absent, so a reader of
`frob.toml` sees every value that governs the repo. Knobs that only
tune performance (thread counts, cache sizes) are not materialized.

### 1.7 Agent-facing surface

- Every verb has `--json` with a schema generated from the response
  type; schemas live under `schema/` and are drift-checked.
- `frob serve` (MCP via rmcp, HTTP for the GUI in cli-contract.md) exposes the
  same handlers with a warm db; the tool list is generated from the
  same `#[derive(Command)]` metadata so CLI and MCP cannot drift.
  grimble exposes its own `serve --mcp` (crate `grimble-serve`: read-only
  `check` and `graph`, token in `params._meta.token` on every request,
  announced once on stderr; synchronous stdio until tokio/rmcp are
  vendored); crunk has no MCP server.
- Exit code 3 refusals carry a machine-readable `retry_after_ms` hint
  when retrying later can succeed (docs/design/shared/cli-contract.md section 2).
- The v1 hook fleet (eight python processes per Bash call) is replaced
  by one `frob hook <event>` subcommand reading the hook JSON on stdin,
  so a hook is one process start of a small binary (docs/design/shared/architecture.md section 1.7).

### 1.8 Key dependencies (pinned in the workspace)

clap 4, salsa 0.28 (milestone 2), tree-sitter 0.27.0 (grammars tree-sitter-rust 0.24.2, tree-sitter-md 0.5.3, tree-sitter-toml-ng 0.7.0, pinned exactly; ast-grep-core 0.45.3 is compatible), rusqlite (bundled), gix 0.87.1 (0.88 does not resolve; reads
and ledger writes; git CLI only per architecture.md), rayon, blake3, serde/toml/toml_edit, jiff, ulid,
ignore/globset, pulldown-cmark, miette (bin only) or annotate-snippets,
tracing, inventory, schemars, rmcp (serve crates only), insta, rstest,
datatest-stable, trybuild, cargo-nextest. Full table with versions and
alternatives: notes/research/rust-ecosystem.md section 2.

### 1.9 Parallelism from day one

Rust has no GIL, so the v1 thread-pool versus process-pool split
disappears; the design still has to make heavy work parallel by
construction rather than by later retrofits.

| Layer | Mechanism | Used for |
|---|---|---|
| data parallelism | `rayon` (work-stealing pool, `par_iter`, `par_bridge`), one global pool sized by `[perf] threads` defaulting to physical cores | file discovery and hashing, parsing, U term building, digests, per-file rules, dup rungs, ticket index rebuild, capability detectors |
| query parallelism (Milestone 2 or later (D36)) | salsa parallel queries on cloned database handles, one handle per request or rayon task, so independent derived queries share memos; see the concurrency model below | graph assembly, per-file findings, affects walks |
| graph algorithms | `petgraph` on immutable snapshots; SCC, closure, and reachability run per connected component in parallel | call graph closure, cycles, grimble kernel |
| external jobs | `gob-exec` bounded job pool (`[perf] jobs`), with per-job timeout, memory cap via cgroup where available, and output caps | test runners, ruff/clippy/tsc, Tailwind helper |
| async IO | `tokio` only in `gob-serve`, `frob-serve`, `grimble-serve`, `frob-gh`; the core stays sync | server transports, HTTP |
| shared state | immutable snapshots passed by `Arc`; `dashmap` only in caches; no locks of our own around derived state (v1's deadlock class); salsa itself may block a thread that waits on a query in flight elsewhere | caches, interned ids |
| SQLite | one file per repository (`$XDG_CACHE_HOME/frob/cache/<repo-id>/frob/cache.sqlite`, rows MAC'd under the machine key (security.md 2.2), shared by every worktree of it); within a process one writer connection behind a channel, many readers in WAL mode; across processes a 5 s `busy_timeout`, an immediate-transaction migration and best-effort writes | persisted artifacts and findings |

Rules for every crate: expensive loops are `par_iter` unless the item
count is bounded and small; a rule's `check` is pure over the snapshot
so the pipeline can schedule it anywhere; nothing holds a lock across a
parse. Memory admission from v1 is kept in spirit: the pool size is
reduced when `MemAvailable` divided by a per-task estimate is lower
than the core count, logged once, never a refusal.

Concurrency model (salsa, Milestone 2 or later (D36)). Each request
or rayon task works on a cloned database handle. Setting an input
cancels in-flight queries on every other handle, so the server catches
the cancellation and retries the request, and the file watcher debounces
input writes (default 200 ms) so a busy editor cannot starve a long
`check`. Queries are pure: persistence is done by the command layer
after the queries return. A spike ticket validating salsa `par_map` on
rayon and the cancellation behaviour is a precondition for committing
to `gob-db`; until then milestone 1 uses plain parallel functions.

Verification: `frob --timing` reports per-stage wall time and the
parallel speedup; a benchmark crate (`criterion`) tracks cold and warm
check on a fixture repo of 100k lines, run in CI on a schedule, with a
regression threshold.

## 2. Git and GitHub without subprocess storms

Provenance: written under T-0001 (a v1-format id that migrates with an alias). Owner direction 2026-10-01: keep everything
automatic for the agent, but minimize process IO. v1 evidence: 370
`git`/`gh` argv literals across 34 modules; one ticket verb commonly
spawned `rev-parse`, `status --porcelain` (several times), `worktree
list`, `add`, `commit`, plus the hook fleet; every spawn paid process
start and re-read the repo from disk.

### 2.1 Principle

One process opens the repository ONCE and does everything through
`gix` (gitoxide) in memory. A subprocess is spawned only for the
handful of operations that need git's own conflict machinery, and
those are listed and counted. GitHub goes over HTTPS from the process,
never through `gh`.

### 2.2 In-process git (gix) covers

| Need | gix facility | v1 spawned |
|---|---|---|
| repo root, common dir, current worktree, HEAD, branch | `gix::discover`, `head()`, `worktrees()` | rev-parse, worktree list |
| dirty check, changed paths vs HEAD or base | `status()` with pathspec, `diff` tree-to-index and index-to-worktree | status --porcelain (x11 shapes) |
| diff vs merge base for touched set and scope checks | `merge_base`, `diff::tree` | merge-base, diff --name-status |
| read a file at a revision | `rev_parse_single`, object lookup | show REV:path, cat-file -e |
| blame, log by path, conventional-commit mining | `blame`, revwalk with path filter | log, show |
| commit the ledger | write blobs and a tree built from the ledger ref's tip plus the changed ticket directory (never from an index), `commit_as` with author from config | add, commit |
| create or move refs with compare-and-swap | `refs::transaction` with expected previous value | update-ref |
| add, list, remove worktrees | `worktree` module (add is newer: verify; fallback below) | worktree add/remove |
| config (user.name, merge drivers, hooks path) | `config_snapshot` | git config |
| tags and release lookup | refs iteration | tag, describe |

Reads are snapshot inputs (salsa inputs from milestone 2) refreshed
from one `gix` snapshot per invocation (or per file-watch event in the
server), so `check`, `ticket`, and `land` share them instead of each
asking git again.

Writes the ledger needs are blob, tree, commit, and ref updates: all
plain object writes that gix does without a worktree touch. A ticket
mutation is therefore: read the tip of the ledger ref (`[tickets] ref`,
default the trunk branch), write blobs for the changed ticket
directory, write a tree equal to the tip's tree with only that
directory replaced, commit, and update the ref by compare-and-swap. The
tree is never built from any index, so staged user changes cannot enter
a ledger commit. If the CAS loses, re-read the tip, rebuild and retry up
to `[git] cas_retries` times (a bounded count with jittered backoff,
never a deadline). The guarantee is that no accepted commit is lost and
that racing writers as a whole always make progress; it is not that
every racer wins, so a writer that loses `cas_retries + 1` times in a
row gets `E-GIT-CAS-EXHAUSTED`. When a checkout has the ledger ref
checked out, its index entries and worktree files for the ledger paths are
updated to match (refused with a remedy if those paths have local
edits). No `git add`, no `git commit`, no hooks unless the repo asks for
them (`[git] run_hooks = true` executes `pre-commit` once via one
spawn). frob/tickets.md section 2 has the full writer story and the CI,
fork and offline cases.

### 2.3 The short list that may spawn

The first table is the closed list of `git` spawns. The second table
is every other class of spawn the design needs; none is git, and all go
through the same runner.

| Operation | Why | Bound |
|---|---|---|
| three-way merge of a worktree branch into the land staging tree when gix's merge reports conflicts needing rename detection or a custom driver | git's merge-ort is the reference; reimplementing conflict resolution is out of scope | at most 1 spawn per land |
| `git worktree add` if the gix worktree write path is not yet complete at the pinned version | verified at build time by a feature test; removed when gix covers it | at most 1 per `work` |
| repo-configured hooks (`pre-commit`, `pre-push`) | they are user programs by definition | 1 per commit or push when enabled |
| `git ls-remote` freshness probe (`GIT_TERMINAL_PROMPT=0`, ssh `BatchMode=yes`, killed at `[sync] probe_timeout_ms`) | gix has no cheap bounded remote ref listing; a spawn can be killed, an in-process transport cannot | at most 1 per ttl per clone, from `frob refresh` |
| `git push` over SSH | gix supports fetch; push transport is newer; use git until gix push is stable | 1 per `--push` |
| user-invoked escape hatch `frob git -- ...` | debugging | explicit |

| Other spawn class | Why | Bound |
|---|---|---|
| test runners and evidence providers | they are the thing being run | one per selected runner, within `[perf] jobs` |
| `[[check.tool]]` entries (ruff, clippy, tsc, cargo doc, mdbook, lychee, typos, markdownlint, zizmor, actionlint, hadolint) | opt-in external linters and doc gates | one per configured tool, concurrent, outside the 2 s check budget |
| sibling `grimble check --json` and `crunk check --json` when not linked in | the orchestrated check | at most 1 per sibling per check |
| `grimble vet --hook`, invoked by `frob hook pre-tool` | the install guard | 1 per guarded call |
| out-of-process helpers (crunk's Tailwind runtime, playwright gallery) | stay out of process | one per crunk run |
| `frob merge-driver`, spawned by git itself | git runs the driver; it is inbound, not a frob spawn | one per conflicted ticket file |

Every spawn goes through one `gob-exec` runner that logs the argv,
duration, and exit under an `exec.spawn` span, so `frob --timing` shows
the count. A repo-internal rule (PROC001, in gob-exec) fails the build if
any crate outside its allow list references `std::process`; the allow
list is `gob-exec`, `gob-git` and `frob` (the binary, whose `main` calls
the process-exit function); `gob-git` spawns through `gob-exec`.
`gob-exec` programs: `Program::Hook` carries the hook path, `Sibling`
resolves next to `current_exe` first, and tool names are open by default
(`Runner::allow_tools` restricts them).
`gob-git` as built (gix 0.87.1): `commit_paths` takes `index.lock` when
the ref is checked out; the local-edits check runs the on-disk bytes
through gix's filter pipeline (core.autocrlf and `.gitattributes` safe)
before comparing; `merge_branch` decides "up to date" in gix and
otherwise spawns one `git merge`; a name without `refs/` resolves as
`refs/heads/<name>`.
`gob-git` also owns the one worktree-content normalizer
(`Repo::worktree_content_as_git`, `WorktreeSource`): a symlink reads as
its target string and a regular file runs through the same clean filters.
Every digest compared with recorded state goes through it (`gob-walk`'s
`ContentSource` for walk digests and symbol extraction), so a CRLF
checkout under `core.autocrlf` hashes like its LF twin. Parsed text is the
normalized text, so spans are offsets into it; line numbers are identical
in both forms.
The normalization costs time in the `walk` stage: measured with
`frob check --timing` on a release build over this repository (warm
caches, three runs), `walk` takes 239-244 ms (it was about 65 ms before
normalization, and about 240 ms in a debug build). That is roughly 3% of
the 7.8-8.1 s check budget, well inside it; the dominant stages are
`file-rules` (about 6.4 s) and `graph` (about 1.1 s). No further walk
optimization is planned unless `walk` exceeds 5% of the budget.

Measured target: a typical ticket verb spawns zero processes; `land`
spawns at most two git processes (merge fallback, hooks); `check` spawns
only the configured external tools and siblings.

### 2.4 GitHub without `gh`

Milestone 2 or later (D36). `frob-gh` (frob only; grimble and crunk have
no GitHub features) talks to the REST and GraphQL API directly
(`octocrab` or a thin `reqwest` client with `ureq` for the sync paths)
using the token from `GH_TOKEN` or `GITHUB_TOKEN`; it does not read
`gh`'s config file, because current `gh` keeps its token in the OS
keyring. Operations: open or update a PR for a landed ticket, read CI
run status and failing jobs, create a release from the milestone, read
issues for `frob migrate tickets --from-github`. Responses are cached
by ETag in `.frob/`. If no token is present the feature reports
`unavailable` with the remedy; it never shells out to `gh` to borrow its
login.

### 2.5 Hooks and the agent harness

v1 spawned up to eight python processes per agent Bash call. v2 ships
one `frob hook <event>` entry that reads the hook JSON on stdin,
evaluates all registered guards in-process (suggest frob verbs, root-
write guard, directive guard, telemetry), and exits. `pre-tool` invokes
`grimble vet --hook` as a sibling spawn when grimble is configured. One
small-binary start per event, no interpreter. Milestone 2 or later
(D36); v1 hooks keep running meanwhile.

### 2.6 Daemon option

Milestone 2 or later (D36). `frob serve` (MCP and HTTP) keeps the gix
repository, the salsa db, and the SQLite index open. When a daemon for
the repo is running, the CLI connects over a Unix socket and the command
executes in the warm process, so even the one process start per verb is
the thin client. The CLI never requires the daemon; it is an
optimization that falls back to in-process execution transparently. Two
safeguards: the CLI and daemon handshake on binary version and schema
version and the CLI refuses to forward on a mismatch (running
in-process instead); and before serving a request the daemon re-stats
the request's inputs, so an edit made a moment ago is never answered
from a stale watcher state. On Windows there is no Unix socket: the
transport is a named pipe, or in-process only until that exists.

### 2.7 Verification

- A test harness counts spawns (via the `gob-exec` registry) per CLI
  scenario and snapshots the counts; a change that adds a spawn to a
  ticket verb fails review.
- gix write paths (commit, CAS ref, worktree add) are covered by
  integration tests against a real temp repo and compared byte-for-
  byte with what `git` produces for the same inputs.

### 2.8 Partial object stores (shallow and overlay checkouts)

A checkout whose object store lacks parts of the base tree (a shallow
clone, or a helper `.git` assembled from a filtered pack such as goway's
`--with-git` overlay) cannot be diffed with a plain tree-to-worktree
status. `diff_names` against the work tree first tries the normal path;
if that fails and some subtree objects of the base are absent, it falls
back to index-vs-worktree status plus a tree-to-index diff over the
subtrees that are present, and reports every file under an absent
subtree as modified (conservative: it may over-select tests, never
under-select). If the base tree itself is absent the result is
`E-GIT-SHALLOW-BASE`, surfaced by `frob test` as `E-TESTS-SHALLOW-BASE`
with the remedy to fetch the base history or pass a base that is present.

## 3. Disciplines: paths and time

Two disciplines share one shape: a small set of types, one reading point, compile-time confinement,
and a lint that holds the line. Paths come first, then time.

### 3.1 Paths: one discipline from type to lint (D86)

Provenance: accepted direction, owner request 2026-10-03 ("structural and
powerful, not a cheap hotfix"). The `/` versus `\` difference broke this
repository's CI on every first Windows run: the merge driver command
line, the command-tool allowlist compare, a `--cwd` string compare, a
fixture name. Each was code that compiles everywhere and is wrong on one
platform. A lint alone finds some of them after they are written. This
design makes the wrong thing hard to write, checks the rest at compile
time, verifies both path styles on one host, and keeps the PATH lint
family (rules.md 3.1) as the second line and as the product feature for
other repositories.

#### 3.1.1 Three kinds of path, three types

| Kind | Type | Separator | Where it lives |
|---|---|---|---|
| Host path: a file on this machine | `std::path::{Path, PathBuf}` | the platform's | in memory, in process arguments, never persisted |
| Repository path: a file named relative to a repository root | `gob_path::RelPath` | `/` by contract | everything persisted or compared across machines: ledger, `frob.lock`, `grimble.lock`, findings JSON, config values, scope globs, the sibling contract |
| Display path: text for a person | `gob_path::Shown` (render-only) | the platform's, home shown as `~` | the rendering layer only |

`RelPath` moves from gob-git to a new leaf crate, `gob-path`, and
becomes the one repository-path type for every crate (25 files use it
today). Its constructors are the only bridges between kinds:

- `RelPath::from_host(root: &Path, p: &Path) -> Result<RelPath>`:
  strips the root by components (`Path::strip_prefix`, never string
  prefixes), refuses a path outside the root, joins components with `/`,
  and refuses a component that is not valid on every supported platform
  (reserved device names, `<>:"|?*`, trailing dot or space, `\`), so a
  name that breaks a Windows checkout cannot enter the repository's data.
- `RelPath::to_host(&self, root: &Path) -> PathBuf`: joins components
  with `Path::join`.
- `Shown::of(p: &Path)`: the only path-to-text conversion for people;
  it scrubs the home directory to `~` (the same rule as the ledger scrub
  of ~33PZ67A, one function).

Persisted model types hold `RelPath`, never `PathBuf` or a path in a
`String`. A host path that must be recorded (a lease's worktree in the
local registry under `.git/`) is local data and says so in its type
(`LocalPath`, not serialized into anything committed).

Status (~YGK8FGN): the `scrub` event's `files` and `digests[].file` are
`RelPath` (validated on read), and `crates/frob-ledger/tests/persisted_paths.rs`
walks the serde-derived types of frob-ledger, gob-lock, gob-diagnostics and
gob-config so a `PathBuf` or a plain-string path field cannot return. The
findings JSON `file` fields stay display strings until ~0EWC4K9.

Status (~ARHP82G): `gob-path` exists with `RelPath` (also validating
components on every platform), `PathStyle` (Unix or Windows, read with
`typed-path`), `RelPath::from_host_style` / `to_host_style` for style-explicit
bridges, and `Shown`. gob-git re-exports `RelPath` and `PathError`;
`RelPath::new` now returns `PathError`, which converts into `GitError`.

Status (~KHR84D9): the gob-* crates (all but gob-path) convert paths to text
only through gob-path and are off the confinement allow list. Lossy display
text is `Shown::with_home(path, None)`; strict text is
`gob_path::exact_text(path) -> Option<&str>`, which returns the path verbatim
or `None` for non-Unicode; tracing fields use the `?path` debug form. Only
the crunk crates remain on `ALLOW`. This section's `Arg` type has not been
added to gob-path; `command_line` callers still pass `OsString` arguments.

#### 3.1.2 Command lines: arguments, never strings

Processes take an argument vector of `OsString` through gob-exec
(PROC001 already confines spawning there); a path is passed as its own
argument and never interpolated. The few places a whole command line
must be one string, because another program parses it (git's
`merge.<driver>.driver` and hook lines, a `.ps1` body, a `sh -c` script),
go through one function:

`gob_exec::command_line(shell: Shell, argv: &[Arg]) -> String`, with
`Shell::{Posix, GitForWindowsSh, PowerShell, Cmd}` and per-shell quoting.
It is property-tested by round trip: for random argv (spaces, quotes,
backslashes, drive letters, `$`, `%`, non-ASCII), splitting the produced
line with a reference splitter for that shell returns the argv exactly.
`frob init` writes the merge driver through it.

No product path needs a POSIX shell. A `[[check.tool]]` stage and a `command`
evidence provider run their program by argv through gob-exec, so a Windows host
without Git for Windows' `usr\bin` on `PATH` runs them unchanged. A shell line
that a user configures is run with the platform shell, quoted by
`command_line`. Tests that exercise `sh` behaviour (fake tool stages, process
group kills) gate on `gob_exec::require_sh(test_name)`, which logs and prints
`SKIPPED <test>: requires prerequisite sh on PATH` and returns false, so a
missing `sh` is a named prerequisite in the report, never a failure.

#### 3.1.3 Compile-time confinement

The workspace `clippy.toml` lists `disallowed-methods` for every
path-to-text conversion (`Path::to_str`, `Path::to_string_lossy`,
`Path::display`, `OsStr::to_str`, `OsStr::to_string_lossy`, and their
`PathBuf` and `OsString` forms) and `disallowed-types` for `PathBuf` in
modules that define persisted types. gob-path is the one crate allowed to
use them (an `#[expect]` with a reason at each site); everything else
goes through `RelPath`, `Shown` or `Arg`. This is the same mechanism as
the owner's "one renderer, no `println!` scattered" rule, and it fails
`cargo clippy -D warnings`, so a new conversion cannot land. The 255
existing conversions in 105 files migrate crate by crate; each
migration ticket ends with that crate free of the allow list.

The allow list is shrink-only and lives in one place: the `ALLOW` array in
`crates/gob-path/tests/it/confinement.rs`. A crate on it carries, at the root
of each target that still converts, `#![expect(clippy::disallowed_methods,
reason = "confinement allow list: ...")]` (`cfg_attr(test, ...)` when only
its unit tests convert). Three failures keep it honest: a new conversion in
an unlisted crate fails `cargo clippy -D warnings` naming the method and the
`gob_path` replacement; a listed crate whose conversions are gone fails
clippy with an unfulfilled expectation, and once the marker is removed the
`confinement` test fails until the crate leaves `ALLOW`; a marker in an
unlisted crate fails the same test. `disallowed-types` for `PathBuf` in
persisted-type modules is not expressible per module in clippy.toml; the
persisted-type check stays with the PATH rules (section 3.1.5).

##### 3.1.3.1 Canonicalization and the deletion jail (~EDPHHFS)

`std::fs::canonicalize` returns a verbatim path (`\\?\C:\...`) on Windows that git and
most tools reject, so it is in `disallowed-methods` (with `Path::canonicalize`) and
`gob_fs::canonical` (crates/gob-fs/src/path.rs; `gob_exec` re-exports it) is the one function that calls it: it strips `\\?\` and `\\?\UNC\`
when every component survives without the prefix (no dot component, reserved device name,
trailing dot or space, `<>:"|?*`, and under `MAX_PATH`), else keeps the verbatim form. Every
product and test call site goes through it. The pure style functions beside it
(`has_dot_component`, `strictly_inside`, `simplify_verbatim`) work on text in either `Style`, so
the Windows rules are tested on Linux.

The garbage collector's jail refuses any `.` or `..` component, split on both `/` and `\\`
in every style, before it touches the file system, and compares canonical forms by whole
normalized components. Note that `PathBuf::join` and `push` onto a verbatim path resolve `..`
lexically on Windows: a test that builds a dotdot path with `join` there tests a different
path than it names, so such inputs are built as text. Until the fix is proven on Windows CI the
automatic pass only reports on Windows (`report_only`).

#### 3.1.4 Both path styles verified on one host

gob-path's logic is written once over a path-style parameter using the
`typed-path` crate (pure-Rust Unix and Windows path semantics on any
host), so the bridges and the component validation are property-tested
with Windows paths on this Linux host: drive letters, UNC prefixes,
mixed separators, case, reserved names. Platform `std::path` is used
only at the outer edge, where the style is the host's. Three layers then
verify the real platform: the Windows-target clippy check before push
(~RBF6057, compile-only), the windows-latest CI job, and `goway run
--host win` before push once the goway Windows host lands (~XKXW2BJ in
goway).

#### 3.1.5 The lint: PATH, for everyone else

Inside this repository the types and clippy confinement are the primary
defence. The PATH family (rules.md 3.1) is the product feature that
brings the same discipline to other repositories and other languages:
PATH001 absolute host path literal, PATH002 separator literal on a path
turned into a string, PATH003 path pasted into a command-line string.
Their remedies name the structural fix (a repository-path type, argv,
one quoting function) rather than a local patch. TICK004 is the data
counterpart for the ledger. In this repository the PATH rules also
check that nothing slips past the confinement through a different
spelling (a format string, a macro).

#### 3.1.6 Order

1. gob-path crate: `RelPath` moved and extended, `Shown`, component
   validation, typed-path property tests; gob-git re-exports for one
   release.
2. `gob_exec::command_line` with round-trip property tests; the merge
   driver and every other single-string command line use it.
3. clippy confinement on, with the allow list initially covering the
   crates not yet migrated; one ticket per crate group removes its
   entries until the list holds only gob-path.
4. Persisted types audited to `RelPath` (ledger, locks, findings, config).
5. PATH family in GRL (~21PHK3V), with this repository's bugs as corpus.

### 3.2 Time: one clock, one zone, from type to lint (D93)

Provenance: section 5 step 1 built (gob-time, one pinned clock in the command context, clippy
confinement); steps 2 and 3 follow. Accepted direction, owner request 2026-10-04 ("Can we add a time
lint?"). ~AAZFNR5 turned CI red at 00:06 UTC: `frob cycle` derived a
cycle's state from the UTC day while the library's `Day::today()` used
the machine's local zone, and the cycle tests hardcoded a "future" date
that became today. Each piece compiled and passed on most runs. As with
paths (D86, architecture.md), a lint alone finds some of this after it is
written; this design makes the wrong thing hard to write in this
repository, and ships the TIME lint family (rules.md 3.2) as the second
line and as the product feature for other repositories.

#### 3.2.1 Four kinds of time, four types

| Kind | Type | Zone | Where it lives |
|---|---|---|---|
| Elapsed time: how long something took | `std::time::Instant`, `Duration` | none | timing, timeouts, backoff; never persisted, never compared across processes |
| Instant: when something happened | `gob_time::Stamp` (UTC, RFC 3339 with `Z`) | UTC | everything persisted or compared: ledger events, leases, evidence, caches, snooze `until` |
| Calendar day: which day something belongs to | `gob_time::Day` | UTC by contract (pm-and-releases.md section 5) | cycles, due dates, release section dates, velocity windows |
| Display time: text for a person | `gob_time::Shown` (render-only) | the user's local zone | the rendering layer only |

`Stamp` and `Day` move to a new leaf crate, `gob-time` (today `Stamp`
lives with the ledger and `Day` in frob-pm), and become the one
instant type and the one day type for every crate. A local-zone value
never enters data; `Shown` is the only conversion to local time, and it
only produces text.

#### 3.2.2 One clock, read once per command

`gob_time::Clock` is a trait with `now() -> Stamp` and `today() -> Day`
(`today` is derived from `now`, never read separately).
`SystemClock` reads the system time; `FixedClock` returns a set
instant. A verb receives its clock from the command context and reads
it once: every date a single command computes or writes comes from one
snapshot, so a command that runs across midnight cannot disagree with
itself. Library code takes `&dyn Clock` (or a `Stamp` it was given);
it never reads the system time.

There is no environment variable or hidden flag that overrides the
clock: docs/design/shared/architecture.md section 1.6 forbids environment that changes an
outcome. Library tests use `FixedClock`. CLI tests never hardcode a
calendar date that is meant to be in the past or future: they build
dates relative to the clock's day (the helpers ~AAZFNR5 introduced),
and a test that needs an exact date (a boundary like 00:06 UTC) is a
library test with `FixedClock`.

#### 3.2.3 Compile-time confinement

`clippy.toml` `disallowed-methods` forbids reading the wall clock
outside `gob-time`: `std::time::SystemTime::now`,
`std::time::SystemTime::elapsed`, `jiff::Timestamp::now`, `jiff::Zoned::now`
and the local-zone constructors (`jiff::tz::TimeZone::system`, `try_system`;
jiff has no civil `Date::today`). The lint is `deny` in the workspace.
`std::time::Instant::now` stays allowed (elapsed time is not a date).
`gob-time` carries the one `#[allow]` with a reason (`src/wall.rs`, the only file that reads the wall clock). As built, the command
context holds one `SystemClock::pin()` snapshot (`Context::clock`), `Ledger`, `LeaseStore` and `Workspace` take the
clock at open, and `Cache` defaults to `SystemClock` (rows are dated, never compared) until `with_clock` replaces it. A crate that needs
the time takes a `Clock`.

#### 3.2.4 The lint family (product feature)

TIME is a grimble family (owner grimble, crate grimble-lints, universal
over U like PATH); rules.md 3.2 has the table. In short: TIME001 flags a
local-zone or naive current-time read whose value is stored, compared
or sent (Python `datetime.now()` without `tz`, `date.today()`,
`datetime.utcnow()`; JS `new Date()` formatted with local getters;
Rust `Zoned::now`, `chrono::Local::now`); TIME002 flags arithmetic or
comparison between a naive and an aware datetime; TIME003 flags a test
that builds or asserts a calendar date literal while the code it reaches
reads the wall clock with no clock injected, the exact shape of
~AAZFNR5. Where the call graph cannot decide reach, TIME003 is
Unresolved, never clean.

#### 3.2.5 Sequencing

1. `gob-time` with `Stamp`, `Day`, `Shown`, `Clock`, `SystemClock`,
   `FixedClock`; migrate every wall-clock read; clippy confinement.
2. TIME001 and TIME002 in grimble-lints for Rust and Python.
3. TIME003 on the call graph, with its fidelity row.

## Decision records

The decisions homed here, moved from the old design/README.md log. The index is [docs/decisions/README.md](../../decisions/README.md), generated from decisions.toml.

### D1

Rust; three binaries (frob, grimble, crunk) over a strictly layered workspace of about 57 small crates

### D10

salsa for in-process incrementality (milestone 2), SQLite for persisted artifacts keyed by content and parser identity

### D16

rayon plus salsa parallel queries everywhere expensive; bounded external job pool; benchmarks in CI

### D30

Speed mechanism (audit H9, M10): "warm" means a fresh process with a populated per-worktree `.frob/` cache; findings are persisted per (file digest, rule id, rule version, side-input digest) plus a graph digest for repo rules; external tool stages and doc gates are outside the 2 s budget; SQLite is per worktree with `busy_timeout`, writes are best-effort and happen from the command layer; the bench crate measures the fresh-process case

### D34

Configuration and idempotency (audit M6, M23): a config inventory table lists every knob with product file, default and owner; every enforcement constant is a knob; `exceptions.toml` is in the storage table; `new` accepts `--idempotency-key` and dedupes only on key or identical request; `batch` is restricted to ledger-only verbs, all or nothing; plan tokens are digests recomputed at apply

### D37

Remaining MEDIUM and LOW audit findings are resolved by applying the audit's suggested fix (first alternative where it offers several); the per-finding record is notes/review/audit-design.md

Also logged against: notes/review/audit-design.md.

### D38

Cache files (T-0011, T-0018): the check cache (gob-cache) is `cache.sqlite` under `$XDG_CACHE_HOME/frob/cache/<repo-id>/<product>/` with a MAC per row, never in the work tree (~H2DAC49, security.md 2.2) and the ledger index is `.frob/tickets.sqlite` (frob-ledger), keyed by the tickets subtree id, not the whole tree; `cache.db` is gone

### D39

Config as built (T-0006, T-0017, T-0019, T-0020, T-0022, T-0031): `[tickets]` (ref default `refs/heads/main`, ref_mode, dir, handle_min_len, actor, the registry_files alias dropped by ~ACRF17G in favour of `[lease] shared_files`), `[check]` (fail_on default `error`, exclude, size_cap), `[git] cas_retries`, `[cache] busy_timeout_ms`, `[lease]`, `[worktree] dir`, `[evidence]`, `[invariants] forbid_imports`; only `enforcement` fields are materialized; the architecture.md inventory lists code and design rows separately

### D42

Pins (T-0004, T-0010, T-0012): tree-sitter 0.27.0 with tree-sitter-rust 0.24.2, tree-sitter-md 0.5.3, tree-sitter-toml-ng 0.7.0; ast-grep-core 0.45.3 is compatible (audit M26 answered); gix 0.87.1 (0.88 does not resolve); gob-text owns TextSize and TextRange (ruff_text_size rejected as unstable)

### D54

gob-config (T-0006): the inventory stores a describe function, `check` returns a `Result`, table paths may be dotted, and `FieldDescription` carries a per-field JSON schema

### D15

Git through gix in one process; subprocess only through gob-exec for a bounded, listed set; no `gh`; spawn counts snapshot-tested

### D52

gob-exec (T-0009): `Program::Hook` carries a path; `Sibling` resolves next to `current_exe` first; tool names are open by default and `allow_tools` restricts them

### D53

gob-git (T-0010, T-0030): `commit_paths` takes `index.lock` for checked-out refs; local-edit detection runs disk bytes through gix's filter pipeline (autocrlf-safe); `merge_branch` decides up-to-date in gix and otherwise spawns one `git merge`; names without `refs/` resolve as `refs/heads/`

### D86

Owner request 2026-10-03, "structural and powerful, not a cheap hotfix": one path discipline (architecture.md). Three path kinds with three types: host `Path`, repository `gob_path::RelPath` (`/` by contract, the only persisted form, component-validated for every platform), display `Shown`; bridges only through gob-path; command lines are argv, and the few single-string lines go through `gob_exec::command_line` with per-shell quoting proven by round trip; clippy `disallowed-methods` confines path-to-text conversion to gob-path; both path styles property-tested on one host with typed-path; then Windows clippy, windows-latest CI and goway. The PATH lint family (PATH001-003, new name, v1 PORT stays dropped) is the second line and the product feature for other repositories

### D93

Owner request 2026-10-04 ("Can we add a time lint?") after ~AAZFNR5: one time discipline (architecture.md). Four kinds with four types in a new leaf crate gob-time: elapsed `Instant`/`Duration`, instant `Stamp` (UTC, the only persisted form), calendar `Day` (UTC by contract), display `Shown` (local, render-only); one `Clock` trait (`SystemClock`, `FixedClock`) passed through the command context and read once per command; no environment or hidden flag overrides the clock (architecture.md 6), CLI tests build dates relative to the clock and exact-boundary tests are library tests with `FixedClock`; clippy `disallowed-methods` confines wall-clock and local-zone reads to gob-time. The TIME lint family (TIME001-003, grimble) is the second line and the product feature for other repositories
