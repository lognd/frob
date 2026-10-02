# frob v2 design

Design-first rewrite of frob in Rust. Start with goals.md, then
products.md and boundaries.md, then the rest. Where files disagree,
the later files win in this order: products.md, boundaries.md,
exceptions.md, documentation.md, pm-enforcement.md, then the README
decision log entries D23 onward. Each file is a DRAFT under T-0001
(a v1-format id; it migrates with an alias) until accepted; accepted files change status to
ACCEPTED and further changes go through tickets.

| File | Covers |
|---|---|
| goals.md | charter, goals, non-goals, principles, binding requirement |
| architecture.md | workspace, data flow, storage, errors, logging, config, agent surface |
| cli.md | verb surface, JSON envelope, exit codes, idempotency, jobs |
| tickets.md | ledger, ids, data model, links, workflow, leases, evidence, landing, Jira mapping |
| code-model.md | symbols, adapters, directive DSL, structural IR, cross-language binds, capability matrix |
| rules.md | rule derive, families, check pipeline, waivers, ratchet |
| grimble-model.md | grimble (.grmb) model grammar, kernel, binding, drift findings, data packs |
| build-test-ci.md | build locality, test kinds, generated artifacts, CI budget |
| monorepo.md | frob, grimble and crunk in one workspace; publishing |
| migration.md | v1 import, rule id map, rollout |
| products.md | frob / grimble (design goblin) / crunk split |
| gui.md | stateless web GUI and TUI over the same handlers |
| pm-enforcement.md | structured user stories, definition of ready/done, velocity-aware cycles, measured forecasts, WIP |
| exceptions.md | accept / defer / hotfix / baseline with machine-checkable exits, budgets, reason quality, EXC rules, migration of v1 waivers |
| documentation.md | one home per kind of knowledge, generated vs written pages, NARR rules that keep ticket narrative out of code, ADRs, changelog fragments, rustdoc discipline |
| boundaries.md | placement test, full capability map per product and crate, splits considered, naming and dependency rules |
| git-io.md | in-process git via gix, bounded spawns, GitHub over HTTPS, one hook binary |

Evidence behind the decisions lives in `notes/`:

| File | What it is |
|---|---|
| notes/v1/cli-surface.md | every v1 verb and flag with keep/merge/drop |
| notes/v1/gates-and-rules.md | all 667 v1 rule ids, pipeline, slowness analysis |
| notes/v1/tickets.md | v1 ticket model, landing, incidents, Jira gap list |
| notes/v1/graph-lang-dsl.md | symbols, digests, lock, DSL, edges, cache, analysis tools |
| notes/v1/strata.md | grammar, kernel, 12 binding mechanisms, rules, adoption |
| notes/v1/ops-and-integrations.md | testing, vet, serve, release, fleet, hooks, telemetry |
| notes/v1/agent-usage.md | what agents actually ran: 36,610 calls, retries, polling, refusals |
| notes/rust-ecosystem.md | ruff/uv/ty patterns, macro recipe, crate picks, workspace |
| notes/jira.md | Jira model, 22 pinch points, 27 competitor concepts, agentic differences |
| notes/crunk.md | crunk survey and FROBLEMS complaints |
| notes/audit-design.md | design audit 2026-10-02: 9 HIGH, 36 MEDIUM, 22 LOW, milestone-1 cut |
| notes/audit-resolution.md | how each audit finding was resolved (applied, decided, deferred) |
| notes/coordinator.md | coordinator state: ground rules, milestone order, status log |

## Decision log

One row per decision, in order. D23 onward resolve the 2026-10-02
design audit (notes/audit-design.md) and override earlier text until
the files are updated.

| # | Decision | Where |
|---|---|---|
| D1 | Rust; three binaries (frob, grimble, crunk) over a strictly layered workspace of about 57 small crates | architecture.md, boundaries.md |
| D2 | ULID ticket ids; no counters, drafts, promote, renumber | goals.md, tickets.md |
| D3 | Rules, directives, capabilities, commands, config tables declared once via derives; docs and schemas generated | rules.md, build-test-ci.md |
| D4 | Two-tier rules: universal over a structural IR, language-specific over tree-sitter | goals.md, code-model.md, rules.md |
| D5 | Symbol addresses are language-neutral; cross-language `binds` edge; capability matrix with reasoned `excuses` | code-model.md, grimble-model.md |
| D6 | The grimble model (v1 strata) keeps node/flow/boundary/claims/V-model; everything else is a data pack | grimble-model.md |
| D7 | Ledger commits are built by frob, not mined from history; no mirror, no splice, no merge queue daemon (writer story refined in D23) | tickets.md |
| D8 | Synchronous land with fast check; deferred-verification machinery not rebuilt | tickets.md, rules.md |
| D9 | frob, grimble and crunk share one workspace with `gob-*` substrate crates | monorepo.md |
| D10 | salsa for in-process incrementality (milestone 2), SQLite for persisted artifacts keyed by content and parser identity | architecture.md, code-model.md |
| D11 | Three products: frob (work accounting), grimble (structure and architecture model, .grmb files), crunk (front-end design system); structural lints and the design model are one tool | products.md |
| D12 | GUI is stateless: web SPA and TUI call the CLI handlers in-process over generated types | gui.md |
| D13 | CLI contract: JSON envelope off-TTY, exit codes 0/1/2/3/4 per the cli.md table (domain state is never a failure; `--fail-on` and `test` opt into exit 1), idempotent verbs, batch updates; no jobs (D25) | cli.md |
| D14 | Jira concepts kept with changed mechanisms: categories plus outcome, typed links with topology, cycles as events, fractional rank, triage inbox, saved queries as boards | tickets.md |
| D15 | Git through gix in one process; subprocess only through gob-exec for a bounded, listed set; no `gh`; spawn counts snapshot-tested | git-io.md |
| D16 | rayon plus salsa parallel queries everywhere expensive; bounded external job pool; benchmarks in CI | architecture.md |
| D17 | Project management is enforced: structured stories, ready/done definitions, capacity-checked cycles, Monte Carlo forecasts from events | pm-enforcement.md |
| D18 | Substrate crates are `gob-*`; products never depend on each other (the `bundle` feature is the one stated exception); grimble and crunk are standalone binaries frob can orchestrate | boundaries.md, products.md |
| D19 | Non-functional goals are quality objectives with a resolvable driver, a registered metric, a measured baseline, a checkable target and a runnable proof; a graph-detected public-surface change forces a user story | pm-enforcement.md |
| D20 | Documentation: reference pages generated from derives, mdbook site, MADR ADRs bound to architecture invariants, towncrier-style fragments, NARR rules forbid ticket narrative in code | documentation.md |
| D21 | Exceptions are one primitive with four kinds (accept, defer, hotfix, baseline) whose exits the tool evaluates; budgets and one reason checker | exceptions.md |
| D22 | Owner decisions 2026-10-02: `gob-` prefix, repo stays `frob`, everything MIT, ULID-only ids, no large blobs in the repo, error_set trial, declarative ast-grep-shaped rules, SARIF inside 2.0, `.grmb` is its own language, no invisible variables, doc lints as errors from day one; crates.io package `frob-cli` | monorepo.md, tickets.md, rules.md, architecture.md |
| D23 | Ledger writer story (audit H1): ledger commits advance the configured ledger ref (`[tickets] ref`, default the trunk branch); the commit tree is built from that ref's tree plus the changed ticket directory, never from any index; the ref is updated by CAS with bounded retry; when a checkout has the ledger ref checked out, frob updates its index and worktree for `tickets/` only; `[tickets] ref = "branch"` mode puts ledger commits on the current branch for protected-trunk and fork flows; TICK rule flags a referenced ticket absent from the base | tickets.md, git-io.md |
| D24 | Ids (audit H2): the full 26-char ULID is the only persisted form in directives, links, trailers and fragments; the human handle is the unique suffix of the random part (shown as `~xxxxxxx`, minimum 7 chars), accepted by every verb; a fixer expands handles on write and a TICK rule flags abbreviated ids in tracked text | tickets.md, goals.md, migration.md |
| D25 | Jobs (audit H3): `land` is synchronous; there are no job ids in milestone 1; `--wait <secs>` bounds lock acquisition only; if jobs ever exist they arrive with the daemon and a job store under `.git/frob/jobs/` | cli.md, tickets.md |
| D26 | Leases (audit H4, M9): `work` and `start` are idempotent only for the same holder (actor plus worktree path); another caller gets exit 3 `E-LEASE-HELD` naming the holder; acquisition runs under one lock file in the git common dir; overlap is glob intersection OR resolved-set intersection; TTL and WIP limits are materialized knobs with WIP off by default; leases are single-clone | tickets.md, cli.md, pm-enforcement.md |
| D27 | Exit codes (audit H5): one table in cli.md with a row per refusal class; `retryable` means the same argv may succeed later without other action; `FROB_CI` is removed in favour of a materialized `[check] fail_on` knob and `--fail-on`; crunk adopts the shared contract; rules.md pipeline step 8 follows cli.md | cli.md, rules.md |
| D28 | Boundaries (audit H6, H7, M14, M17): ticket-bound exception exits and the close guard are evaluated by frob only, from sibling `--json` in which `ticket=` is opaque; standalone grimble and crunk report such exceptions as Unresolved; lock and ack mechanics move to `gob-lock` with one lock file per product (`frob.lock`, `grimble.lock`) and an `ack` verb per product; `.grmb` `waive` becomes the four exception kinds; frob consumes grimble entities and `binds` edges only through `grimble --json`; PM026 uses the gob-symbols public-API graph only | exceptions.md, grimble-model.md, boundaries.md, code-model.md |
| D29 | Server security (audit H8): `frob serve` is read-write; a per-launch random token is mandatory; Origin and Host are checked against the bound address; mutations require a JSON content type | gui.md, goals.md |
| D30 | Speed mechanism (audit H9, M10): "warm" means a fresh process with a populated per-worktree `.frob/` cache; findings are persisted per (file digest, rule id, rule version, side-input digest) plus a graph digest for repo rules; external tool stages and doc gates are outside the 2 s budget; SQLite is per worktree with `busy_timeout`, writes are best-effort and happen from the command layer; the bench crate measures the fresh-process case | architecture.md, rules.md |
| D31 | Crate split (audit M1): imports and the call graph live in gob-symbols; gob-ir holds only the structural IR; gob-db (salsa) is a milestone-2 crate | boundaries.md, code-model.md |
| D32 | Rule identity (audit M3, M4, M5): EXC replaces WAIVE and DEBT everywhere; one family-to-crate table in boundaries.md covers every family; ids are FAMILYNNN with an optional slug alias in all products; grimble policy rules use `GPOL`; PARSE and DSL live in gob-directives and are emitted under the parsing product's namespace; policy files live next to the owning product's config | rules.md, boundaries.md, grimble-model.md |
| D33 | Ticket model (audit M7, M8, M29): statuses are categories plus close guards, no transition graph; the terminal field is `outcome`; priority is `low|medium|high|critical`; `blocked` is derived; `milestone` is a release object, not a ticket type; the planning unit is `cycle`; one canonical link table with inverses; one event-kind table; non-ticket events live under `events/` at the repo root; frontmatter integrity means "equals the fold of events"; the merge driver unions events and re-folds, and `frob init` or `doctor` installs it | tickets.md, pm-enforcement.md |
| D34 | Configuration and idempotency (audit M6, M23): a config inventory table lists every knob with product file, default and owner; every enforcement constant is a knob; `exceptions.toml` is in the storage table; `new` accepts `--idempotency-key` and dedupes only on key or identical request; `batch` is restricted to ledger-only verbs, all or nothing; plan tokens are digests recomputed at apply | architecture.md, cli.md |
| D35 | Publishing (audit M19): crates.io receives the full crate set at release in lockstep versions because `frob-cli` depends on them; binaries ship via cargo-dist and PyPI; names are reserved at first publish | monorepo.md, products.md |
| D36 | Milestone 1 (audit M34, L22): frob checks and lands in this repository with Rust, markdown and TOML adapters only; no grimble, crunk, GUI, daemon, jobs, salsa, IR, PM forecasting or Jira-parity features; the crate cut is the table at the end of notes/audit-design.md | build-test-ci.md, monorepo.md, notes/coordinator.md |
| D37 | Remaining MEDIUM and LOW audit findings are resolved by applying the audit's suggested fix (first alternative where it offers several); the per-finding record is notes/audit-resolution.md | notes/audit-resolution.md |
