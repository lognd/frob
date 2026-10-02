# Audit resolution: how each finding in notes/audit-design.md was closed

Pass over docs/design/*.md on 2026-10-02 that propagates the audit
(notes/audit-design.md, 67 findings) and decision-log rows D23 to D37
(docs/design/README.md) into the design files. Where the audit's
suggested fix and a D-row differ, the D-row won. "applied" means the
audit's suggested fix (first alternative where it offered several) was
written into the named files; "decided Dnn" means the README decision
row is the authority and the files now state it.

## Resolution table

| Id | Severity | Resolution | Files touched |
|---|---|---|---|
| H1 | HIGH | decided D23 (ledger ref, tree built from ref tip, CAS retry, `ref = "branch"`, TICK absent-from-base, new CI/fork/offline section 2b) | tickets.md, git-io.md, architecture.md |
| H2 | HIGH | decided D24 (full ULID persisted, `~handle` from random suffix, fixer plus TICK rule) | tickets.md, goals.md, migration.md, code-model.md, documentation.md, cli.md |
| H3 | HIGH | decided D25 (synchronous land, no jobs, `--wait <secs>` bounds lock acquisition) | cli.md, tickets.md, boundaries.md, gui.md, architecture.md |
| H4 | HIGH | decided D26 (same-holder idempotency, `E-LEASE-HELD`, one lock file) | tickets.md, cli.md, pm-enforcement.md |
| H5 | HIGH | decided D27 (exit-code table in cli.md, `retryable` defined, `[check] fail_on` replaces the environment switch, crunk adopts contract, rules.md step 8) | cli.md, rules.md, architecture.md, boundaries.md, goals.md |
| H6 | HIGH | decided D28 (ticket-bound exits evaluated by frob from sibling `--json`, `ticket=` opaque, Unresolved standalone, `.grmb` waive becomes the four kinds) | exceptions.md, boundaries.md, grimble-model.md, products.md, code-model.md |
| H7 | HIGH | decided D28 (`gob-lock`, `grimble.lock`, `grimble ack`) | grimble-model.md, boundaries.md, products.md, cli.md, exceptions.md |
| H8 | HIGH | decided D29 (read-write server, mandatory per-launch token, Origin and Host checks, JSON content type) | gui.md, goals.md |
| H9 | HIGH | decided D30 (warm defined, persisted findings keys, tool stages outside budget, bench measures fresh process) | architecture.md, rules.md, goals.md, code-model.md, boundaries.md |
| M1 | MEDIUM | decided D31 (imports and call graph in gob-symbols, gob-ir structural IR only, gob-db milestone 2) | boundaries.md, code-model.md, monorepo.md, architecture.md |
| M2 | MEDIUM | applied (`bundle` exception stated, Unresolved per missing sibling, `schema_version` check) | boundaries.md, products.md, architecture.md |
| M3 | MEDIUM | decided D32 (EXC replaces the v1 waiver and debt families; Directive derive example is `defer`; migrate subverb is `exceptions`) | code-model.md, rules.md, products.md, boundaries.md, grimble-model.md, migration.md, cli.md, exceptions.md |
| M4 | MEDIUM | decided D32 (one family-to-crate table, boundaries.md 2.5; GPOL vs POL; one policy file location each) | boundaries.md, rules.md, grimble-model.md, documentation.md |
| M5 | MEDIUM | decided D32 (FAMILYNNN with slug alias; grimble ids rewritten as one table; many-to-one migration stated) | grimble-model.md, code-model.md, rules.md |
| M6 | MEDIUM | decided D34 (config inventory table in architecture.md section 6; constants became knobs; grimble knobs in grimble.toml; exceptions.toml in storage table) | architecture.md, grimble-model.md, exceptions.md, tickets.md, cli.md, rules.md, pm-enforcement.md, goals.md, monorepo.md |
| M7 | MEDIUM | decided D33 (categories plus close guards, `outcome`, priority enum, derived `blocked`, milestone is a release object, `cycle`, one canonical link table) | tickets.md, pm-enforcement.md, migration.md, cli.md |
| M8 | MEDIUM | decided D33 (event-kind table, root `events/`, frontmatter equals fold of events) | tickets.md, pm-enforcement.md, exceptions.md, migration.md, architecture.md |
| M9 | MEDIUM | decided D26 (glob intersection OR resolved sets, TTL knob, single-clone, WIP off, non-symbol regions are file scope) | tickets.md, pm-enforcement.md, architecture.md |
| M10 | MEDIUM | decided D30 (per-worktree SQLite, `busy_timeout`, best-effort writes from the command layer) | architecture.md, boundaries.md, code-model.md, git-io.md |
| M11 | MEDIUM | applied (concurrency model subsection: handle cloning, cancellation retry, debounce, spike precondition) | architecture.md, gui.md, git-io.md |
| M12 | MEDIUM | applied (capacity unenforced until `min_history`, forecast Unresolved with sample count, pooled throughput) | pm-enforcement.md |
| M13 | MEDIUM | applied (drivers resolved at transition and recorded, tracked baselines instead of telemetry files) | pm-enforcement.md |
| M14 | MEDIUM | decided D28 (PM026 uses gob-symbols public-API graph only; `close` and `land` outside the 100 ms budget with a measurer timeout knob) | pm-enforcement.md, boundaries.md, architecture.md |
| M15 | MEDIUM | applied (attested digest in `exceptions.toml`, STALE only from a fresh full evaluation, fingerprints without line numbers, REATTEST clock from the change commit date) | exceptions.md, rules.md |
| M16 | MEDIUM | applied (`n/a` reported as one Unresolved per node, CAP003 Advisory for one release, SYS003 opt-in via `[grimble] modeled`) | code-model.md, grimble-model.md |
| M17 | MEDIUM | decided D28 (frob consumes grimble entities and `binds` only through `grimble --json`; census verb is grimble's) | grimble-model.md, tickets.md, boundaries.md, code-model.md, products.md |
| M18 | MEDIUM | applied (`frob hook pre-tool` invokes `grimble vet --hook` as a listed sibling spawn) | boundaries.md, git-io.md |
| M19 | MEDIUM | decided D35 (crates.io receives the full crate set in lockstep; binaries via cargo-dist and PyPI) | monorepo.md, products.md, build-test-ci.md |
| M20 | MEDIUM | applied (source-namespaced aliases, ULIDs from v1 created dates, only current acks carried, `aliases` field, goals non-goal updated) | migration.md, tickets.md, monorepo.md, goals.md |
| M21 | MEDIUM | applied (doc gates and GEN001 are `[[check.tool]]` stages of this repo; changelog compilation owned by frob-release, called by gob-dev) | documentation.md, build-test-ci.md, boundaries.md |
| M22 | MEDIUM | applied (quarantine to a tracked file and deferred to milestone 2, local artifacts to `.git/frob/artifacts`, principle lists the deliberate non-git state) | rules.md, tickets.md, architecture.md, goals.md, cli.md |
| M23 | MEDIUM | decided D34 (`--idempotency-key`, `batch` ledger-only and all or nothing, plan tokens as recomputed digests) | cli.md |
| M24 | MEDIUM | applied (redactor in gob-log, applied by gob-exec capture; the ledger scan is a TICK rule rather than SEC because frob cannot depend on grimble-security) | architecture.md, tickets.md, boundaries.md |
| M25 | MEDIUM | applied (review stated as an audit trail, `[exceptions] owners` defined) | exceptions.md, gui.md, tickets.md, architecture.md |
| M26 | MEDIUM | applied (ast-grep-core decided pending a spike; both files say so) | code-model.md, rules.md |
| M27 | MEDIUM | applied earlier by the coordinator (README rewritten before this pass; not touched here) | README.md |
| M28 | MEDIUM | applied (verb table regenerated: verb, product, crate, idempotent, exit codes, milestone; `status` and `migrate` resolved; hidden `merge-driver` kept) | cli.md, tickets.md, boundaries.md, migration.md |
| M29 | MEDIUM | decided D33 (driver unions events and re-folds; init or doctor installs it; TICK re-fold in CI) | tickets.md |
| M30 | MEDIUM | applied (version and schema handshake, daemon re-stat, Windows named pipe or in-process) | git-io.md |
| M31 | MEDIUM | applied (`verify = "ci"` and quarantine deferred with the requirements they need) | rules.md, tickets.md, architecture.md, boundaries.md |
| M32 | MEDIUM | applied (boundaries.md 2.6 gives each KEEP item an owner or a dropped reason) | boundaries.md, cli.md, tickets.md |
| M33 | MEDIUM | applied (write-time refusal follows rule severity; composition of the three strictness knobs) | rules.md, pm-enforcement.md |
| M34 | MEDIUM | decided D36 (self-hosting is frob-only in milestone 1) | build-test-ci.md, monorepo.md |
| M35 | MEDIUM | applied (milestone 1 supports `dir:` and https; retention and Unmeasured stated) | tickets.md |
| M36 | MEDIUM | applied (ADR files named `<date>-<slug>.md` with generated display numbers; NARR id pattern defined; fragments by full ULID) | documentation.md, exceptions.md, grimble-model.md |
| L1 | LOW | applied (search-and-replace of old names; gob-symbols and gob-ir replace the retired syntax-crate name; section 2.1 completed) | grimble-model.md, code-model.md, goals.md, architecture.md, rules.md, boundaries.md, monorepo.md, products.md |
| L2 | LOW | applied (numbered refs, placeholders, v1 ticket ids, list and section order) | boundaries.md, goals.md, tickets.md, code-model.md, build-test-ci.md, grimble-model.md, products.md, monorepo.md |
| L3 | LOW | applied (one path table in documentation.md section 3; others link to it) | documentation.md, build-test-ci.md, rules.md, code-model.md, architecture.md, goals.md, boundaries.md, exceptions.md, gui.md, monorepo.md |
| L4 | LOW | applied (real substrate DAG, gob-dev marked as the one binary) | architecture.md, boundaries.md |
| L5 | LOW | applied (`tier` split from `scope`, fix enum mapped to A/B/C, TOML severity spelling stated) | rules.md |
| L6 | LOW | applied (`serve --mcp` everywhere, `grimble-serve` crate, crunk has no MCP, tokio list updated) | cli.md, boundaries.md, architecture.md |
| L7 | LOW | applied (watchers removed from goals; LSP, SCIP and PyO3 listed as deferred) | goals.md, boundaries.md |
| L8 | LOW | applied (environment tokens only) | git-io.md |
| L9 | LOW | applied (all spawn classes listed; only gob-exec references `std::process`) | git-io.md, boundaries.md |
| L10 | LOW | applied (one definition of which types count) | pm-enforcement.md, tickets.md |
| L11 | LOW | applied (section 6 describes inference first) | code-model.md |
| L12 | LOW | applied (fold order by ULID time, `at`, file name; ties concurrent) | tickets.md |
| L13 | LOW | applied (display prefix is output-only; directives take full ULIDs) | tickets.md |
| L14 | LOW | applied (every Status line notes T-0001 is a v1-format id with an alias) | all design files except README.md |
| L15 | LOW | applied (REL003 is the only fragment-present rule) | documentation.md, pm-enforcement.md, rules.md, tickets.md |
| L16 | LOW | applied (census verb is `grimble check --census`) | code-model.md, boundaries.md |
| L17 | LOW | applied (size cap, parse timeout, 2-line binding rule, `frob:tests` reorientation stated as unchanged) | code-model.md |
| L18 | LOW | applied (generated mdtest with a firing and a non-firing case per rule) | rules.md |
| L19 | LOW | applied (JUnit added to gob-diagnostics, milestone 2) | boundaries.md |
| L20 | LOW | applied (single `--ticket` definition with `[check] ticket_hops`) | rules.md, cli.md |
| L21 | LOW | applied (worktree path convention and reuse rule) | cli.md |
| L22 | LOW | decided D36 (deferred designs kept and marked "Milestone 2 or later (D36)") | build-test-ci.md, monorepo.md, goals.md, gui.md, pm-enforcement.md, tickets.md, code-model.md, rules.md, grimble-model.md, boundaries.md, git-io.md, exceptions.md, migration.md, architecture.md |

## Judgement calls worth a second look

- Defaults in the architecture.md config inventory (TTL 120 minutes,
  `mega_glob_files` 500, `max_age_days` 60, `cas_retries` 5,
  `measurer_timeout_secs` 600, `capacity min_history` 3) are proposed
  initial values, not measured ones.
- The EXC004 clock starts at the commit date of the change that made the
  digest differ, so nothing extra is stored; the audit offered a stored
  detection time instead.
- Spike tickets (salsa on rayon, ast-grep-core tree-sitter unification)
  are named as preconditions in the files but not filed; no ticket
  tooling was run in this pass.
- The `ticket migrate` verb listed in tickets.md was dropped in favour of
  `frob migrate tickets`, so there is one migration verb group.
