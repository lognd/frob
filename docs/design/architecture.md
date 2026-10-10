# Architecture: workspace, data flow, errors, logging

Status: current
Owner: gob
Decisions: none
Audience: contributor

Provenance: written under T-0001 (a v1-format id that migrates with an alias).
Inputs: notes/rust-ecosystem.md, notes/v1/ops-and-integrations.md
(telemetry), notes/v1/gates-and-rules.md.

## 1. Shape

Three binaries (`frob`, `grimble`, `crunk`) from one Cargo workspace,
strict downward dependencies, about 65 crates in four groups (D1 said
about 57 before D56-D60 added gob-check, gob-pattern, grimble-ci and
the gob-ir layering; boundaries.md section 4 has the count). The
authoritative capability-to-crate map is boundaries.md; the shape:

```
crates/
  gob-*        substrate, depends only on gob-*:
               text config languages symbols directives rules macros
               diagnostics fix walk cache git exec cli log lock serve
               mdtest dev; milestone 2 or later (D36): db (salsa), ir
               (the universal model, below symbols), check (shared
               pipeline), pattern (ast-grep-shaped engine)
  frob-*       ledger pm lease worktree evidence tests obligations ack land
               release fleet explore check gh hook serve
  grimble-*    model kernel bind capabilities lints arch security vet packs
               ci check serve
  crunk-*      values spec ingest tailwind rules tokens query gallery adapters
  frob, grimble, crunk     thin binaries
```

`gob-dev` is the one substrate crate that is a binary: the `cargo dev`
generator (ruff's ruff_dev pattern), never shipped. Layering, enforced
by a repo-internal rule over Cargo metadata and by the dependency graph:
`gob-*` depends only on `gob-*`; product crates depend on `gob-*` and
their own product; products never depend on each other, with the one
stated exception that the `frob` binary with feature `bundle` links
`grimble-check` (which drives the shared `gob-check` pipeline) and crunk's check crate to run them in-process
(boundaries.md section 6). Within the substrate the real order is:
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

## 2. Data flow of one invocation

1. `main` builds `Cli` (clap derive via `gob-cli`), installs tracing,
   opens the repository once through `gob-git` (gix, no subprocess),
   opens the repository-shared cache (`<git common dir>/frob/cache/frob/cache.sqlite`), records invocation start (telemetry spans the WHOLE
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
   file of this repository, shared by its worktrees (`<git common dir>/frob/cache/frob/cache.sqlite`): parse artifacts keyed by
   (content blake3, adapter id, grammar version, schema version, and
   from milestone 2 a digest of the `[compute]` config; the scope graph
   is a repo-scope artifact keyed by the graph digest, code-model.md
   section 8); per-file findings keyed
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
4. Render through `gob-diagnostics`; every finding carries a remedy
   string generated from the rule's `fix_title` or `remedy` doc section.
5. Exit code per the table in cli.md section 2: 0 ok (domain state such
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
budget; they obey the timeout contract of cli.md section 3. The bench
crate measures the fresh-process case.

## 3. Storage

| Artifact | Location | Tracked |
|---|---|---|
| tickets | `tickets/<ulid>/ticket.md` (TOML frontmatter + markdown) | yes |
| ticket events (comments are events) | `tickets/<ulid>/events/<ulid>.toml` | yes |
| non-ticket events (budget raises, audits, reviews of exceptions) | `events/<ulid>.toml` at the repo root | yes |
| acks | `frob.lock`, `grimble.lock` (one lock file per product, `gob-lock`) | yes |
| exceptions | `exceptions.toml` (one array per product: `[[frob.exception]]`, `[[grimble.exception]]`, `[[crunk.exception]]`; the accept digest lives in the lock, exceptions.md section 2) | yes |
| ratchet pools | `frob-ratchet.lock.json`, `grimble-ratchet.lock.json` | yes |
| quarantine (Milestone 2 or later (D36)) | `frob-quarantine.json` | yes |
| design model | `design/*.grmb` (grimble) | yes |
| invariants, decisions | `invariants/INV-*.md`, `docs/decisions/*.md` | yes |
| config | `frob.toml`, `grimble.toml`, `crunk.toml` (one per product) | yes |
| pack drift-lock | `grimble.packs.lock` (one per repository, written only by `grimble packs update`; packs.md section 4) | yes |
| leases | `<common_dir>/frob/leases/<ulid>.toml` plus one `<common_dir>/frob/leases.lock`; single clone, shared by its worktrees | no |
| local evidence artifacts | `.git/frob/artifacts/` (non-authoritative; a missing blob reads as Unmeasured; old unreferenced blobs are collected) | no |
| garbage-collection stamp | `<common_dir>/frob/gc.json` (last pass, throttle) | no |
| cache, index, telemetry | `.frob/` per worktree: `tickets.sqlite` (frob-ledger index, keyed by the tickets subtree id, not the whole tree), plus `cache.sqlite` (gob-cache) once per repository under the git common dir | no, delete-safe |

Nothing authoritative under `.frob/`. Deleting it costs one cold parse.
The deliberate non-git state is exactly: leases (loss means locks
vanish; no data is lost), local evidence artifacts (loss degrades
verdicts to Unmeasured, which is never a finding on a terminal ticket),
and the per-worktree cache. Plan tokens are digests recomputed at apply
and stored nowhere; there is no job store in milestone 1.

### Garbage collection (~BZXZK29)

frob owns local state and the build output of the checkouts it manages, so
it also keeps them under budget; goway owns its remote hosts and their own
collection. There is no collection verb. An opportunistic pass runs inside
verbs that already run often and are about to need disk: `frob work` (before
a new worktree builds) and `frob land` (after the worktree is removed), and
unthrottled from `frob doctor --fix`. `frob doctor` itself runs a dry pass and
reports it. A stamp `<common_dir>/frob/gc.json` throttles automatic passes to
one per `[gc] interval_secs` (default 1 h) and records the last pass for
`doctor`; free space below `[gc] guard_min_free_gb` (default 20 GiB, 0 turns it
off) overrides the interval. The pass is bounded by `[gc] time_limit_secs`,
never fails the verb (every problem is a warning in the verb's output and a log
line), and logs a summary at info.

What is collected, in order, each category with its own knob:

| Category | Rule |
|---|---|
| worktrees | finished ticket worktrees (tickets.md, "Worktree garbage collection"); never one with uncommitted changes |
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

## 4. Errors

Library crates return `Result<T, E>` with per-crate error sets. The
house idiom is typani's ErrorSet; in Rust that is `error_set!` (crate
`error_set`), trialled first in `frob-ledger` (decided 2026-10-02;
notes/rust-ecosystem.md flags its miette interop as unverified); if its miette interop
disappoints, fall back to `thiserror` enums with a shared `Code` trait.
Trial outcome (milestone 1): `error_set` is kept in `frob-ledger`; the
other crates written so far (for example `gob-exec`) use `thiserror`
enums.
Rules for every crate:

- Every error variant has a stable code (`E-LEDGER-NOTFOUND`) and a
  remedy string; `gob-diagnostics` renders both. Codes are collected by
  `cargo dev gen` into the generated errors page (documentation.md
  section 3).
- Panics are programmer bugs. `unwrap` is denied by clippy config
  outside tests; `expect` requires a message naming the invariant.
- No defensive handling of impossible states: unreachable arms use
  `unreachable!("why")` and are covered by a test if reachable.
- Guards (refusals such as "dirty root", "lease held") are not errors;
  they are a `Refusal` type with exit code 3 and a remedy, so agents can
  distinguish "retry after X" from "bug".

## 5. Logging and telemetry

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
the args shape. A TICK rule scans `tickets/**/events/*.toml` for the
same patterns so a transcript that bypassed capture is still caught.

No `println!` outside the renderer crate; clippy `print_stdout` denied
elsewhere.

## 6. Configuration

Each product has one config file (`frob.toml`, `grimble.toml`,
`crunk.toml`), each one serde model with `deny_unknown_fields` (kills
the eleven v1 `*SCHEMA001` gates), loaded by `gob-config`. Each table is a struct with
`#[derive(ConfigTable)]` which emits the JSON schema fragment and the
generated config reference page (documentation.md section 3) from doc
comments (uv's OptionsMetadata pattern). As built (`gob-config`): the derive-registered inventory stores each
table's describe function rather than a value; `load` layers defaults,
file and overrides with per-key provenance and rejects unknown keys with
a did-you-mean; table paths may be dotted (`tickets.lease`); `check`
returns a `Result` so an unreadable file is not silently clean; and each
`FieldDescription` carries a per-field JSON schema. Layering: workspace file, then per-crate or per-dir
`frob.toml` overrides (Combine derive), then CLI flags. `frob config
show --effective` prints the merged result with provenance.

Config inventory. This table is the one place that lists every knob;
"materialized" means `frob init` writes it with its default and CFG001
flags its absence. Defaults are the initial values proposed by this
design.

In code, "materialized" is carried by the `enforcement` marker on a field (only enforcement fields are written by `frob init`); `materialize` on a table is a declaration that its enforcement fields are written.

Rows marked (M1) exist in code at milestone 1 and match the `ConfigTable`
structs of crates/frob/src/config.rs and the sibling crates' `config.rs`
files exactly (the generated docs/reference/config.md is the live copy);
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
| `[gc]` (~BZXZK29: `enabled`, `interval_secs`, `time_limit_secs`, `guard_min_free_gb`, `incremental_max_age_secs`, `target_budget_gb`, `keep_recent_secs`, `keep_binaries`, `cache_budget_mb`, `artifact_retention_days`, `worktrees`) | frob.toml | no | on; 1 h interval, 30 s bound, 20 GiB guard, 6 h incremental age, 30 GiB per-checkout budget (see Garbage collection, section 3) | frob-worktree |
| `[evidence] allowed_tools` (M1) | frob.toml | no | `["cargo", "git", "pytest"]` | frob-evidence |
| `[evidence] inline_max_bytes` (M1) | frob.toml | no | 16384 | frob-evidence |
| `[evidence] store` (M1) | frob.toml | no | `"dir:.git/frob/artifacts"` | frob-evidence |
| `[evidence] timeout_secs` (M1) | frob.toml | no | 1800 | frob-evidence |
| `[evidence] nextest_profile` (M1) | frob.toml | no | empty (nextest's own default) | frob-evidence |
| `[invariants] forbid_imports` (M1) | frob.toml | no | empty (entries of `from`, `to`, `reason`) | frob-obligations |
| `[check] fail_on_unresolved` | frob.toml | yes | `"required"` (`"never"` or `"all"`; the one gate mechanism, cli.md section 2; today gob-diagnostics skips Unresolved, Milestone 2 item 1) | frob (config), gob-diagnostics |
| `[check] require_siblings` | frob.toml | yes | true (a configured sibling that is absent or incompatible is a required Unresolved) | frob-check |
| `[check] sibling_timeout_secs` | frob.toml | yes | 120 (wall-clock bound of one sibling `check --json` run; expiry is a required Unresolved `SIB001` with reason `timeout`; sibling-contract.md section 7) | frob-check |
| `[check] strictness` | frob.toml | yes | `"warn-new-rules"` | frob-check |
| `[check] ticket_hops` | frob.toml | yes | 1 | frob-check |
| `[check] new_rule_warn_releases` | frob.toml | yes | 1 | gob-rules |
| `[[check.tool]]` | frob.toml | no (opt-in list) | none | frob-check |
| `[land] verify` | frob.toml | yes | `"sync"` (`"ci"` is Milestone 2 or later (D36)) | frob-land |
| `[land] push` | frob.toml | yes | false | frob-land |
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
| `[neat] require_effects` | grimble.toml | yes | false (candidate to default on for the public surface of this repository, neatness.md section 5) | grimble-lints |
| `[neat.effects]` vocabulary tables (clock, rng, env, fs, net, stdio, exit per language) | grimble.toml | no (registry; defaults generated for Rust, Python, TypeScript, Go from the gob-ir vocabulary) | generated | grimble-lints |
| `[ci] allow_tag_pins_for` | grimble.toml | yes | empty (verified publishers allowed to tag-pin) | grimble-ci |
| `[ci] max_timeout` | grimble.toml | yes | 30 (minutes; `timeout-minutes` ceiling) | grimble-ci |
| `[ci] contexts` | grimble.toml | yes | the attacker-controlled context set of cicd.md section 5 | grimble-ci |
| `[ci] registries` | grimble.toml | no (registry) | the publish-step vocabulary of cicd.md section 5 | grimble-ci |
| `[ci] max_age_days` | grimble.toml | yes | 365 | grimble-ci |
| `[pm] strict`, `stories_required` | frob.toml | yes | false, true | frob-pm |
| `[pm] max_story_points`, `max_chore_points` | frob.toml | yes | 8, 2 | frob-pm |
| `[pm] max_objective_share` | frob.toml | yes | 0.4 | frob-pm |
| `[pm] max_age_days` | frob.toml | yes | 60 | frob-pm |
| `[pm] capacity_k`, `capacity_points`, `min_history` | frob.toml | yes | 0.5, unset, 3 | frob-pm |
| `[pm] sprint_gate` | frob.toml | yes | true; with a cycle active, `work` and `start` refuse a ticket outside it with `E-PM-NOT-IN-CYCLE` (expedite exempt, `--unplanned --reason` assigns it as an over-commit) | frob-pm, frob-worktree |
| `[pm] max_duplicate_objective_text` | frob.toml | yes | 3 | frob-pm |
| `[pm] measurer_timeout_secs` | frob.toml | yes | 600 | frob-pm |
| `[pm.wip] in_progress_per_identity` | frob.toml | yes | 1 (0 is off); the one per-holder limit, applied by the lease store | frob-pm, frob-lease |
| `[pm.wip] in_progress` | frob.toml | yes | 2 (0 is off); `work` and `start` refuse past it with `E-WIP-REPO` | frob-pm, frob-worktree |
| `[pm.ready]`, `[pm.done]`, `[pm.personas]`, `[pm.attributes]`, `[pm.metrics]` | frob.toml | yes (ready, done), no (registries) | pm-enforcement.md | frob-pm |
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
| `[packs] enabled` | grimble.toml | yes | the three built-ins of packs.md 8 (`grimble/core-effects`, `grimble/ci-github`, `grimble/rust-ecosystem`); a pack not listed is off and a model naming it is MDL009 | grimble-capabilities |
| `[packs] lock` | grimble.toml | yes | `"grimble.packs.lock"` (path of the drift-lock, one per repository; packs.md 3.6 and 4) | grimble-capabilities |
| `[[packs.external]]` | grimble.toml | no | none (url plus digest per external pack, vendored; packs.md 3.4) | grimble-capabilities |
| `[packs.severity]` | grimble.toml | no (only when it differs) | empty (repository override per atom and rule, wins over the pack; equal to the pack value is PACK008; packs.md 3.6 and 5) | grimble-capabilities |
| `[neat.effects.exclude.<lang>]` | grimble.toml | no | empty (names removed from the effect vocabulary, each with a `because`; packs.md 3.6) | grimble-capabilities |
| `[[policy]]`, `rules/*.grl.toml` (code) | grimble.toml and next to it | no | none | grimble-lints |
| crunk tables | crunk.toml | per notes/crunk.md section 4 | per crunk | crunk crates |

`[compute]` is a substrate table with one home: `frob.toml`, read
identically by every product (a standalone grimble with no `frob.toml`
reads the same table from `grimble.toml`; when both files exist,
declaring it in `grimble.toml` is a CFG finding). Sibling `--json`
carries the compute-config digest and frob treats a mismatch as an
incompatible sibling (a required Unresolved, cli.md section 2), so two
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
tree; `frob doctor` logs their locations (`frob init` to follow); a malformed file makes writes refuse (fail closed). The locations
are resolved by `gob-config` (`user_file`, `repo_file`); the engine is `frob-ledger::redact` (tickets.md section 9).

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

## 7. Agent-facing surface

- Every verb has `--json` with a schema generated from the response
  type; schemas live under `schema/` and are drift-checked.
- `frob serve` (MCP via rmcp, HTTP for the GUI in gui.md) exposes the
  same handlers with a warm db; the tool list is generated from the
  same `#[derive(Command)]` metadata so CLI and MCP cannot drift.
  grimble exposes its own `serve --mcp` (crate `grimble-serve`); crunk
  has no MCP server.
- Exit code 3 refusals carry a machine-readable `retry_after_ms` hint
  when retrying later can succeed (cli.md section 2).
- The v1 hook fleet (eight python processes per Bash call) is replaced
  by one `frob hook <event>` subcommand reading the hook JSON on stdin,
  so a hook is one process start of a small binary (git-io.md section 5).

## 8. Key dependencies (pinned in the workspace)

clap 4, salsa 0.28 (milestone 2), tree-sitter 0.27.0 (grammars tree-sitter-rust 0.24.2, tree-sitter-md 0.5.3, tree-sitter-toml-ng 0.7.0, pinned exactly; ast-grep-core 0.45.3 is compatible), rusqlite (bundled), gix 0.87.1 (0.88 does not resolve; reads
and ledger writes; git CLI only per git-io.md), rayon, blake3, serde/toml/toml_edit, jiff, ulid,
ignore/globset, pulldown-cmark, miette (bin only) or annotate-snippets,
tracing, inventory, schemars, rmcp (serve crates only), insta, rstest,
datatest-stable, trybuild, cargo-nextest. Full table with versions and
alternatives: notes/rust-ecosystem.md section 2.

## 9. Parallelism from day one

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
| SQLite | one file per repository (`<git common dir>/frob/cache/frob/cache.sqlite`, shared by every worktree of it); within a process one writer connection behind a channel, many readers in WAL mode; across processes a 5 s `busy_timeout`, an immediate-transaction migration and best-effort writes | persisted artifacts and findings |

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
