# Charter: goals, products, monorepo and boundaries

Status: current
Owner: gob
Decisions: none
Audience: contributor

The charter of frob, grimble and crunk: what the project is for (part 1), the product split (part 2), the
shared workspace (part 3) and the boundaries with their one placement test and one crate table (part 4).
Merged from the former goals.md, products.md, monorepo.md and boundaries.md.

## 1. Goals and principles

Provenance: written under T-0001 (a v1-format id that migrates with an alias). This
file is the charter; the architecture lives in `architecture.md` and each
subsystem has its own file.

### 1.1 One sentence

frob v2 is a fast Rust binary that is the project-management and work-
accounting layer for a repository: a git-tracked ticket ledger that
supersets Jira, enforced project-management discipline, and gates that
make unaccounted-for work a build failure. It ships from one workspace
with two sibling goblins (charter.md part 2 and part 4): grimble, the
structural and design linter whose `.grmb` model binds to code symbols
across languages, and crunk, the front-end design-system linter. All
three share the `gob-*` substrate crates.

### 1.2 Why rewrite

v1 is ~320k lines of Python plus two PyO3 kernels. It works, and the
ideas are right, but:

- Every invocation pays ~8s of fixed overhead before any gate runs; a
  full `frob check` on its own repo is minutes. Agents loop on it.
- The rule set grew by accretion: 20+ gate families, 900+ tickets of
  history, and schemas declared via `module:symbol` strings in TOML.
  Adding a rule touches five files and a docs table.
- Filing ONE ticket in a fresh repo today prints five warnings and two
  errors and returns a draft id (observed 2026-10-01 while seeding T-0001).
- Tests and builds are monolithic; a one-line change reruns everything.

### 1.3 Goals (ranked)

1. Speed. Warm `frob check` on a 100k-line repo in under 2s ("warm" is
   a fresh process with a populated per-worktree `.frob/` cache, not a
   daemon; docs/design/shared/architecture.md section 2); any ticket read in under 50ms and
   any ticket mutation in under 100ms; cold graph build bounded by
   tree-sitter parse time, parallel across cores, incremental by file
   digest. External tool stages and doc gates are outside the 2s budget.
2. Project management that supersets Jira, in-repo, git-merged: tickets,
   epics, cycles, milestones, components, custom fields, links,
   comments, queries, boards, and automation rules (local hooks and
   policy rules; there are no watchers), all as text that merges
   cleanly. Milestone 1 (D36) is the ledger core; the rest is Milestone
   2 or later (D36).
3. System design + symbolic binding (grimble): a `.grmb` model whose entities bind
   to symbols (not globs) in any supported language, with drift detected
   per facet, and with design decisions, invariants, threats, and
   evidence as first-class, queryable entities. Milestone 2 or later
   (D36).
4. Macro-driven, boilerplate-free rules: a rule is one Rust item with a
   derive; id, docs, severity default, fix title, schema, and the
   generated rule reference page are all derived. Same pattern for CLI commands,
   config tables, directives, and ticket fields.
5. Modular workspace: many small crates, strict layering, feature-gated
   grammars, so a change to one subsystem rebuilds and retests only that
   subsystem.
6. Agile by default: zero-config start (`frob init` then `frob ticket
   new` with no errors), sensible defaults, progressive strictness, and
   project-management discipline that is enforced rather than documented
   (pm-and-releases.md: structured stories and quality objectives,
   definitions of ready and done, capacity-checked cycles, measured
   forecasts; cycles and forecasts are Milestone 2 or later (D36)).
7. Observability: structured `tracing` everywhere, every invocation
   recorded, every slow path explainable with `--timing`.
8. Minimal process IO: git through gix in-process, a counted short list
   of spawns, no `gh` (architecture.md); expensive steps parallel from day one
   (docs/design/shared/architecture.md section 1.9).

### 1.4 Non-goals

- Code navigation/editing (LSP clients do that). Consuming LSP or SCIP
  data is deferred: Milestone 2 or later (D36), no crate yet.
- A hosted web service. Local-first; the optional `frob serve` (MCP and
  HTTP) is read-write behind a mandatory per-launch token (cli-contract.md); it
  is a thin view over the same handlers, not a second code path.
- Byte-compatibility with v1 on-disk formats. A one-shot `frob migrate`
  imports v1 tickets, `frob.lock`, config, waivers and directives
  (migration.md); nothing else carries, and `.strata` models are rewritten by hand (D136).
- Python interop in the core. PyO3 bindings are an optional leaf crate:
  Milestone 2 or later (D36), no crate in charter.md yet.

### 1.5 Principles

- Tracked text is truth; `.frob/` is a cache that may be deleted at any
  time. The only deliberate non-git state is leases, the local evidence
  artifact store and per-worktree caches, each with stated loss
  semantics (docs/design/shared/architecture.md section 3); none of it is authoritative.
- Every fallible operation returns `Result<T, E>` with a typed error set;
  panics are programmer bugs. (`error_set!` style unions, `miette` for
  rendering, `tracing` for logs; see `architecture.md`.)
- Every violation message carries its remedy command.
- Every rule, command, directive, config key, and ticket field is
  declared ONCE in Rust and everything else (docs, schema, completions,
  reference tables) is generated and drift-checked in CI.
- Debt is visible or it does not exist: exceptions carry a kind, a
  reason and a machine-checkable exit and show in every report; cut
  scope is a dropped ticket with a reason.
- ASCII only, no emoji, conventional commits.
- No invisible variables: every policy knob (PM thresholds, exception
  budgets, strictness, thresholds, TTLs) is written into the config file
  by `frob init` with its default, and a missing known knob is a config
  error, so behaviour is always readable from the repo (architecture.md
  section 6). No environment variable changes an enforcement outcome;
  `FROB_LOG` filters logs and `FROB_AGENT` only labels the actor.
- MIT licensed, all three products and the substrate.

### 1.6 Ticket identity decision

v1 used `T-####` counters, which collide across worktrees and forced the
`T-draft-<hex>` promote dance. v2 ticket ids are time-ordered and
collision-free at creation: a ULID, 26-char Crockford base32. The full
ULID is the only persisted form (directives, links, commit trailers,
changelog fragments, file names). Humans use a short handle: the unique
suffix of the random part of the id, shown as `~xxxxxxx` with at least
7 characters, accepted by every verb (`frob ticket show ~6C0D1E2`); a
fixer expands handles to full ids on write and a TICK rule flags
abbreviated ids in tracked text. Counters are gone; `frob ticket
renumber` and `promote` are gone with them. Rationale and alternatives
(UUIDv7, KSUID, hash ids) are in `tickets.md`.

### 1.7 Requirement: universal symbolic binding and two-tier rules

Stated by the user on 2026-10-01; this constrains `code-model.md`
and `rules.md`.

Milestone 1 (D36) implements the symbol grammar and the language-specific
tier; the universal structural model and the universal rules over it are Milestone 2
or later (D36).

- One symbol address grammar for every supported language. A grimble
  node, a ticket, a doc anchor, a test, and a rule finding all point at
  code the same way, regardless of language. Binding is to symbols and
  patterns, never only to file globs.
- Patterns span languages. "Sort inside a loop", "network call inside a
  retry loop", "secret in a string literal" are ONE rule each, written
  once against the universal structural model (universal-model.md), and
  executed per language by an adapter. Language-specific structural lints (a Python
  mutable default argument, a Rust `unwrap` in a library crate) are
  declared in the same rule framework but target one grammar.
- Capability binding keeps the v1 matrix idea: every grimble node
  declares the capabilities it `may` use; a capability a node does not need is
  excluded explicitly with a reason, never silently. The matrix is
  generated from rule metadata plus the model, so adding a capability
  kind or a language does not require touching every node by hand.
- Scaling rule: adding a language is one adapter (parse, rho, bind, cap)
  plus a fidelity corpus, and zero changes to universal rules; adding a
  universal rule is one Rust item and zero changes to adapters.

## 2. Products

Provenance: written under T-0001 (a v1-format id that migrates with an alias). Owner direction 2026-10-01: make the
responsibilities of frob and crunk unmistakable; rename strata (v1 name) into its
own goblin-named tool; decide whether the structural linter and the
design model belong together.

### 2.1 The split

| Product | One-line job | Owns | Never does |
|---|---|---|---|
| frob (ticket goblin) | accounts for WORK: tickets, scope leases, worktrees, evidence, landing, releases, the obligation gates that tie code to tickets, docs, and tests | the frob-tickets ledger branch, frob.lock acks, frob-ratchet, invariants/, decisions/, land, release, fleet, MCP for agents | parse CSS semantics, judge architecture, lint code style |
| grimble (the design goblin) | judges STRUCTURE: the architecture model (what v1 called strata), symbol binding, capability matrix, universal and language-specific structural lints, neatness (NEAT), CI and Dockerfile policy (CI, DK), cycles, dup, dead code, arch metrics, security patterns | design/*.grmb, `grimble.lock`, packs/, rule packs for code structure | know what a ticket is (it parses `ticket=` in an exception as an opaque string), land anything |
| crunk (front-end design-system goblin) | judges front-end DESIGN TOKENS: palette, scales, organization, Tailwind, contrast, token export, gallery; and, as a rule pack (D88/D89), front-end web lint (accessibility, SEO, launch readiness, markup and asset performance) | crunk.toml, tokens, CSS/TSX ingest, gallery | know what a ticket is (same opaque `ticket=` rule), model architecture |

The placement test that decides which product owns a capability is stated once,
in part 4 section 2.1 of this charter.

### 2.2 Do the structural linter and the design model belong together?

Yes, one tool. Reasons:

- They share every input: the code graph (symbols, U terms, imports, calls,
  effect sites) and the rule framework. Splitting them means two tools
  parsing the same tree.
- Half of the structural lints are only meaningful against the model:
  undeclared flow, capability exceeded, surface drift, layering.
  The other half (sort in loop, mutable default, cycles, dup) are the
  same rule shape with no model input. One registry, one `check`.
- A user adopting the tool starts with the model-free lints and grows
  into the model; one binary makes that a config change, not a second
  install.

So: the design goblin = architecture model + binding + all structural
rules. The model language keeps a name of its own inside the tool (the
file format), the way `Cargo.toml` is a format inside cargo.

### 2.3 Naming (decided 2026-10-01)

The design goblin is **grimble** (owner: reminiscent of "grumble", what
you do when you realize you started with a bad design). Binary
`grimble`, crates `crates/grimble-*`, model files `design/*.grmb`, the
model language is called grimble too; "strata" survives only as the v1
name in notes/ (no migration path, D136). Availability checked 2026-10-01:
free on crates.io and PyPI. Alternatives considered: gnarl (PyPI taken),
snag and skulk (both taken), krenk (free, too close to crunk).

### 2.4 Name reservation (checked 2026-10-02)

| Name | crates.io | PyPI | Action |
|---|---|---|---|
| frob | taken by an unrelated 2022 crate (`panicbit/frob`, 0.1.2) | ours already | decided 2026-10-02: the Rust crate publishes as `frob-cli` (binary name stays `frob`, like `ruff_cli`); PyPI `frob` keeps shipping the wheel that bundles the binary; a transfer request for `frob` may be sent in parallel |
| grimble | reserved 2026-10-02 | reserved 2026-10-02 | done |
| crunk | reserved 2026-10-02 | ours already | done |
| gob-* | `gob` itself is taken; `gob-rules`, `gob-macros` reserved 2026-10-02; `gob-symbols`, `gob-ir` reserved at first publish | prefixed names free | crates.io receives the full crate set at release in lockstep versions (docs/design/shared/charter.md section 4, D35); names are reserved at first publish |
| frob-cli | reserved 2026-10-02 | not needed | done |

How to reserve: publish a minimal placeholder crate (version 0.0.0,
a README stating the intent, `description` and `repository` set) with
`cargo publish` after `cargo login` with a crates.io API token; crates.io
discourages squatting but accepts placeholders with a real project
behind them. On PyPI, upload a 0.0.0 sdist with `uv publish` (token
from the PyPI account) for `grimble`; PyPI has no reservation API.
crunk lives in this monorepo and the legacy `lognd/crunk` repository is
archived, so no separate repositories are planned; the `grimble` name on docs sites is automatic. The owner
holds the tokens, so this is a `! cargo login` / `! uv publish` step in
the terminal, not something the agent does.

### 2.5 Install story

Three binaries from one workspace, released independently
(`frob-v*`, `grimble-v*`, `crunk-v*`). D87 (owner decision 2026-10-03):
**one binary per package, composed by dependencies.**

| Channel | frob | grimble | crunk |
|---|---|---|---|
| PyPI (prebuilt wheels, five platforms) | `frob`: the `frob` binary only; depends on `grimble` and `crunk` pinned to the same version, so `pip install frob` / `uv tool install frob` installs all three | `grimble`: the `grimble` binary only, installable alone | `crunk`: the `crunk` binary only, installable alone (crunk lives in this monorepo and publishes from it; the legacy `lognd/crunk` repository is archived) |
| crates.io (source) | `frob-cli` (binary `frob`) and its library crates | `grimble` and its library crates | `crunk` and its library crates (the `crunk-*` crates exist in this workspace) |
| GitHub release | one archive per binary and platform | same | same |

No package carries another product's binary, so installing `frob`
and `grimble` side by side never puts two `grimble` executables on PATH
and versions cannot skew. Each PyPI project has one trusted publisher
for this repository (`release.yml`, environment `pypi`).

**Sibling discovery.** `uv tool install frob` exposes only `frob` on
PATH; its dependencies' executables sit in the same tool environment.
frob therefore looks for a sibling first next to its own executable
(the same `bin`/`Scripts` directory, resolved through symlinks; on
Windows, where uv and pipx put a copy of `frob.exe` in a bin directory
instead of linking it, also the `Scripts` directory of the tool
environment named `frob` under the installers' tool roots: `UV_TOOL_DIR`,
uv's default data directory, then pipx's venvs directory, accepted only
when it is a virtual environment holding `frob.exe`; `PATH` is not
consulted for this), then on PATH, and reports which one it used (`check`: `data.siblings`; `doctor`: `siblings`, with any second copy and its version). A user who wants `grimble` on
PATH as well runs `uv tool install grimble`. frob can still link a
sibling's crates in-process when built with the `bundle` feature
(`frob-cli`'s optional `grimble` and `crunk-check` dependencies); a
build without it (crates.io `frob-cli`) that cannot find a configured
sibling reports it as a required Unresolved finding rather than
omitting it, and treats a sibling whose `--json` has another
`schema_version` the same way (exit 1 under the default
`[check] fail_on_unresolved = "required"`, docs/design/shared/cli-contract.md section 2;
docs/design/shared/charter.md section 2.6).

### 2.6 One product front end (D97)

Measured 2026-10-06: `crunk/src/check.rs` and `grimble/src/check.rs` share
106 of 142 lines, the two `doctor.rs` and `workspace.rs` files overlap,
and three crates (`crunk-check`, `grimble-check`, `frob-check`) each build
the `gob.sibling/1` document (sibling-contract.md) with their own
`sources_of`, `finding_json`, rules and exceptions code, while
`frob-check` parses it a fourth way. Every new product or pack would copy
them again.

Decision: the product-neutral parts move down once.

- `gob-check::sibling` owns the `gob.sibling/1` document: one emitter
  from a `CheckRun` (findings, rules, exceptions, sources) and one parser
  (`frob-check` merges through it). The schema is generated from its
  types, so the contract has one owner and one schema test.
- A new crate `gob-product` (above `gob-check` and `gob-cli`) holds the
  `Product` trait: name, config root, how to run a check over a
  workspace, extra doctor rows, extra verbs. It provides the generic
  `check`, `doctor` and workspace discovery verbs; `crunk` and `grimble`
  binaries become a `Product` impl plus `gob_product::main::<P>()`.
  frob adopts the same trait for `check` and `doctor`; its other verbs
  stay frob's.
- Generated artifacts (schemas, reference pages) are registered by each
  product through an `inventory` entry that `cargo dev gen` iterates, in
  place of product-specific calls in `gob-dev`. `gob-dev` still links the
  products (inventory needs the code linked), but it no longer names
  their functions, so adding a product is a registration, not a gob-dev
  edit.

## 3. Monorepo

Provenance: written under T-0001 (a v1-format id that migrates with an alias). Inputs: notes/v1/crunk.md (crunk survey and its
FROBLEMS.md complaints), notes/research/rust-ecosystem.md section 1 (ruff/ty
layout).

### 3.1 Decision

One repository, one Cargo workspace, one `Cargo.lock`, three shipped
binaries (`frob`, `grimble`, `crunk`; charter.md), shared `gob-*`
crates that are published in lockstep versions because `frob-cli`
depends on them (section 4, D35). This is the astral layout: ruff and ty
live in one tree and share `ruff_db`, `ruff_python_parser`, `ruff_text_size`,
`ruff_source_file`, `ruff_diagnostics`.

Why: twelve of the fourteen infrastructure concerns in crunk duplicate
frob (tree-sitter parsing, spans, rule declaration and docs, findings
and rendering, waivers, config, autofix, file walking, caching, CLI
scaffolding, test harness, logging). crunk already pins tree-sitter off
frob and was bitten by the same ABI break. Separate repos would mean a
publish-bump-adopt cycle on every shared API change. And crunk's
FROBLEMS.md is mostly frob mishandling a downstream consumer; with crunk
in the tree, frob's CI tests a real consumer by construction.

### 3.2 Layout

```
crates/
  gob-*             substrate (charter.md section 4.2.1)
  frob-*            project management and work accounting
  grimble-*         structural and design linting
  crunk-*           front-end design system
  frob, grimble, crunk    binaries
  gob-dev           cargo dev generator for all three (the one substrate binary, never shipped)
events/             non-ticket events (frob/tickets.md section 2.4)
docs/
  design/           this set
  frob/ grimble/ crunk/   per-product docs (generated rule and CLI pages inside)
packs/              grimble data packs
(frob-tickets)      one ledger on the orphan branch, `component` field distinguishes products
```

Shared crates carry the `gob-` prefix (not `frob-`) so grimble and
crunk are not second-class citizens in their own code.

### 3.3 What the shared layer must support for grimble and crunk

- Directive namespaces: `crunk:defer`, `grimble:accept` and `frob:ticket`
  come from the same parser with a namespace parameter; a verb belongs
  to the product that consumes it, and a repo declares which namespaces
  it honours in `[directives] namespaces` (docs/design/shared/architecture.md section 1.6).
- Rule id namespaces: a product registers its families (COLOR, SPACE,
  TW...) in the same `#[derive(Rule)]` registry; frob's gates never
  treat a foreign family as unknown (the GATERULE001 complaint).
- Autofix with tiers: crunk's byte-range edits with tolerance become
  Tier A fixes; the shared fix crate adds overlap resolution, dry-run
  diff, and atomic write.
- Languages: CSS/SCSS and TS/TSX adapters live in `gob-languages`;
  crunk's typed TS wrapper, module graph and const-eval move into
  `gob-symbols` and `gob-ir` where grimble's call graph and frob's xref
  also benefit.
- Out-of-process helpers (crunk's node Tailwind runtime, playwright
  gallery) stay out-of-process behind the `gob-exec` sandboxed runner
  with timeout, env scrubbing, and output caps, which frob's test
  runners also use.

### 3.4 Migration order

Milestone 1 (D36): frob checks and lands in this repository with the
Rust, markdown and TOML adapters only; the crate cut is the table at the
end of notes/review/audit-design.md. Steps 2 to 4 below, and everything about
grimble and crunk, are Milestone 2 or later (D36); the milestone-2
order is the one statement in build-test-ci.md (Milestone 2). Status:
the `frob` binary and the substrate and product crates listed in
build-test-ci.md exist under `crates/`, `frob-check` and `frob-land`
have landed, and step 1 is complete only when the self-host switch
lands.

1. frob v2 core and binary reach self-hosting (frob checks this repo).
2. grimble is split out of the initial frob tree into `grimble-*`
   crates as soon as the first structural rule exists; the substrate is
   `gob-*` from the first commit (no rename step).
3. Done: crunk lives in this monorepo and the legacy `lognd/crunk` repository is
   archived. crunk v2 crates are built against `gob-*`; crunk v1 (Python) stayed
   released from its own repo until crunk v2 passed crunk's existing
   system tests (1158 tests; the markdown corpora port first). The
   parity harness (`crates/crunk/tests/parity.rs`) runs the Rust crunk
   over the frozen corpus in `tests/crunk-parity/`; every difference is
   listed with a reason in `tests/crunk-parity/divergences.toml`, and
   the harness fails on an unlisted difference or a stale entry. It runs
   in the CI `crunk` job (`cargo test -p crunk`).
4. Done: the crunk repo is archived; its ticket history was imported with `frob migrate
   tickets --from ../crunk --component crunk`, with aliases namespaced by
   source repo (`crunk:T-0042`) so they cannot collide with frob's own
   `T-0042` (migration.md).

### 3.5 Decided (2026-10-02)

- Repository name stays `frob` (the umbrella, like `ruff` hosting ty).
- License: everything MIT, including the frob binary (v1 was
  GPL-2.0-only). The repo `LICENSE`, README badge, and `Cargo.toml`
  `license = "MIT"` on every crate change in the first scaffolding
  ticket; the v1 branch keeps its GPL history untouched.
- Substrate prefix is `gob-` (as in glob). The crates.io name `gob`
  itself is taken (a 2018 serde codec), which does not matter: the
  prefixed names (`gob-rules`, `gob-symbols`) are free and are published
  with the rest of the crate set (section 4). See docs/design/shared/charter.md section 2.4
  for name reservation.

## 4. Boundaries and placement

Provenance: written under T-0001 (a v1-format id that migrates with an alias).
Supersedes the crate list in docs/design/shared/architecture.md section 1 and refines
charter.md. Owner question 2026-10-02: where exactly do the boundaries
sit, is grimble a standalone binary, should there be more splits, and
are the crates named right?

### 4.1 The placement test

Each product answers one question. A capability goes where its
question lives; if it answers none, it is substrate.

| Product | Question | Needs to know about |
|---|---|---|
| frob | Is this work accounted for and well managed? | tickets, leases, worktrees, evidence, docs claims, acks, releases, cycles |
| grimble | Is the code shaped the way the design says? | symbols, imports, calls, effects, the architecture model, dependency manifests |
| crunk | Does the front end obey the declared design system? | design tokens, CSS/TSX values, Tailwind, screens |
| substrate (`gob-*`) | none; libraries every product needs | text, parsing, config, rules, diagnostics, git, exec, cache |

Decision rule for a rule id: if it still makes sense in a repository
with no tickets, no docs policy and no release process, it is grimble.
If it joins against tickets, docs, acks, tests, or release state, it is
frob. If it needs a `crunk.toml`, it is crunk. By this test the NEAT,
CI and DK families (code neatness, and rules over the repository's own
automation files) are grimble; frob only orchestrates the bound tool
stages that feed them (section 4.2.5).

All three are standalone binaries with their own config file
(`frob.toml`, `grimble.toml`, `crunk.toml`), their own `check`, and
their own release tag; frob and grimble expose `serve --mcp`, crunk has
no MCP server. frob is additionally the orchestrator: `frob check` runs
sibling checks in-process when built with the `bundle` feature or by
invoking the sibling binary's `--json` when installed separately (one of
the allowed spawns), and merges findings into one report. A sibling whose
config file exists but whose check is unavailable (not installed, or its
`--json` carries a different `schema_version`) yields one Unresolved
finding per missing product, marked `required`: under the default
`[check] fail_on_unresolved = "required"` it fails the gate with exit 1
(docs/design/shared/cli-contract.md section 2 is the one definition), so a check never silently
omits a family. grimble and crunk never call frob.

### 4.2 Capability map

Every capability named in the other design files and the v1 inventories.

#### 4.2.1 Substrate crates (`gob-*`, library only except `gob-dev`)

| Crate | Owns | Why shared |
|---|---|---|
| gob-text | TextSize, TextRange (own newtypes; `ruff_text_size` rejected as an unstable internal crate), LineIndex, spans | every finding has a span |
| gob-db | salsa database trait, File inputs, system abstraction; Milestone 2 or later (D36) | incremental core for all three |
| gob-config | TOML loading, layering (Combine), `ConfigTable` derive, schema emit, located errors, missing-knob detection | three config files, one loader |
| gob-languages | tree-sitter grammars (feature-gated, including `actions` and `dockerfile`), the open Language registry, extension dispatch, location sorts | crunk needs CSS/TS, grimble needs all, frob needs comment extraction |
| gob-symbols | the adapters that produce U terms for Rust and markdown (and, with their gob-languages features, GitHub Actions and Dockerfile): parse query, container model, symbol addresses, facet digests (scheme per universal-model.md 7.1), imports with Must/May/Unknown edges, call graph, public-API graph, effect-site extraction, explore views | the code-intelligence substrate; frob (xref, drift, affects, touched-set tests, semver), grimble (everything), crunk (TS module graph) |
| gob-ir | the universal model U (universal-model.md): terms, scope graph with Must/May/Unknown, canonical facet stream, query interface, Kleene evaluator and answer lattice, atom registry and callee vocabularies; below gob-symbols, linked by frob and grimble; Milestone 2 or later (D36) | universal rules, capability detectors, digests, polarity; one model for every product |
| gob-directives | comment/markdown directive parser with a namespace parameter (`frob:`, `grimble:`, `crunk:`), `Directive` derive, exception grammar (accept, defer, hotfix), PARSE and DSL findings | one DSL, three namespaces |
| gob-rules | Rule trait, RuleMeta (with polarity and needs), Severity, Finding (with `subjects_examined`, `source_rule`, `location`), exception parsing, matching and reason checking (EXC), ratchet pool, inventory registry, family namespaces; today exception application still lives in frob-obligations (`apply_exceptions`) and ticket G06 moves it here | one registry across products so `frob check` can merge |
| gob-macros | `Rule`, `Directive`, `Capability`, `Command`, `ConfigTable`, `TicketSchema`, `message_formats` | proc macros, tiny, stable |
| gob-diagnostics | renderers: text with remedy, JSON envelope, GitHub annotations, SARIF and JUnit (Milestone 2 or later (D36)); the exit-code contract of docs/design/shared/cli-contract.md section 2, shared by all three binaries | one output contract |
| gob-fix | Edit, Fix with tiers A/B/C, overlap resolution, dry-run diff, atomic write, fix journal, parse-or-rollback validation (`apply_validated`: a rewritten file that fails its re-parse keeps its pre-fix bytes and is reported `RolledBack`, never written; identical insertions at one point are planned once) | frob gates, grimble lints, crunk token rewrites all fix |
| gob-walk | file discovery over `ignore`, globset, selectors (`path::qual` globs) | scope leases, owns selectors, crunk globs |
| gob-cache | SQLite store per worktree keyed by content, parser identity, schema version; findings table; `busy_timeout`, best-effort writes, WAL readers | parse artifacts, findings, ticket index, crunk cache |
| gob-git | gix repository handle, snapshot of HEAD/status/diff/worktrees, ledger commit and CAS ref writes (architecture.md); every spawn goes through gob-exec | frob (ledger, land), grimble and crunk (diff-scoped checks) |
| gob-exec | the only crate that references `std::process`: bounded job pool, timeouts, env scrubbing, output caps with redaction, spawn registry and counter | test runners, external linters, Tailwind helper, git fallbacks, siblings |
| gob-lock | lock file format (typed entries, `digest_scheme`), ack mechanics and the ack planner, one file per product (`frob.lock`, `grimble.lock`), the shared `ack` implementation | frob acks, grimble drift acks |
| gob-cli | clap conventions: global flags, `--json/--text/--schema`, did-you-mean, completions, help generation, `schema` | identical surface in three binaries |
| gob-log | tracing subscriber setup, telemetry record, redaction, `--timing` span tree | one observability story |
| gob-serve | MCP transport plumbing: per-launch token (D29) checked on every request, newline-delimited JSON-RPC over stdio, read-only tool annotations. Today synchronous with no tokio or rmcp (neither is vendored yet); the HTTP, SSE and Origin side lands with the GUI server on tokio | tools and routes stay per product |
| gob-mdtest | markdown corpus harness over datatest-stable | rule tests in every product |
| gob-check | the product-neutral check pipeline: tool-output parsers (`tool_parse.rs`: SARIF, cargo, ruff, ESLint, typos, formatter check mode, stylelint, zizmor, actionlint), snapshot core, file and repo rule caches, `--only` with known sibling families, exception application, render (milestone 2, ticket G06; grimble/grmb-spec.md 20.2) | `frob check` and `grimble check` run one pipeline |
| gob-plan | the GRL lexer, parser and printer, catalog checks, the plan format (IR, codec, validator), the plan executor and codegen (docs/design/shared/packs-and-plugins.md section 10, grl-spec.md) | frob, grimble and crunk run one rule language |
| gob-pattern | the pattern engine for declarative rules: ast-grep shape at grammar level and over U roles (milestone 2, ticket G17, blocked by the `Doc`-over-U spike of docs/design/shared/rules.md section 3) | GPOL and NEAT-style rule files in every product |
| gob-dev | the `cargo dev` binary (never shipped, links no frob crate): `cargo dev gen` for every product (rule docs, CLI docs, schemas, config docs, TS types; it calls frob-release for the changelog), repo-internal rules (PROC, dependency layering) | one generator |

#### 4.2.2 frob (project management and work accounting)

| Crate | Capabilities |
|---|---|
| frob-ledger | ticket files, ULID ids and handle resolution, `TicketSchema` schema, events, comments, links with topology, custom fields, index, query language, merge driver, `migrate` from v1 |
| frob-pm | types and hierarchy requirements, structured stories, definitions of ready/done, cycles, velocity, capacity checks, forecasts (Monte Carlo, Little's law), flow metrics, WIP limits, `stats`, PM rule family; Milestone 2 or later (D36) |
| frob-lease | scope leases in `.git/frob/leases` taken under one lock file, overlap on glob intersection or resolved file sets (symbol sets and append mode: Milestone 2 or later (D36)), TTL and heartbeat, steal, doable, wave, contention |
| frob-worktree | `work`: worktree create or reuse (path convention in docs/design/shared/cli-contract.md section 3), merge of main, start; `worktree sweep` and `remove`, reconcile |
| frob-evidence | evidence providers (pytest, cargo test, ctest, vitest, junit, command), verdicts, acceptance binding, repro-at-parent, done-report composition |
| frob-tests | touched-set selection from the gob-symbols graph and the diff, runner templates per language, coverage stamp |
| frob-obligations | the accounting rule families of section 4.2.5 (DRIFT through NARR and POL), and the ticket-bound exception exits EXC003 and EXC007 with the close guard (EXC005, the accept digest check, is emitted here too in milestone 1) |
| frob-ack | `frob.lock` symbol entries (format, mechanics and, from ticket G05, the ack planner in gob-lock), acks with reasons, stale and dangling detection, rename candidates, `why` and `affects` views |
| frob-land | the land transaction, CAS publish, passenger detection, deletion filter, LAND-PROOF, the land lock and `--wait <secs>` (no jobs) |
| frob-release | release objects, version authority, changelog fragments and `frob release changelog` compilation, semver from the gob-symbols public-API graph, stamp, publish |
| frob-fleet | fleet manifest, cross-repo status and routing; Milestone 2 or later (D36) |
| frob-explore | outline, map, xref, docs search, graph query (thin views over gob-symbols; also exposed by grimble, see 3.3) |
| frob-check | orchestration of frob's families plus sibling products over gob-check, selection, `--ticket` scoping, id maps for `[[check.tool]]` (the tool-output parsers live in gob-check `tool_parse.rs`), `status` |
| frob-gh | GitHub over HTTPS: PR for a land, CI status, releases, issue import (Milestone 2 or later (D36)) |
| frob-hook | `frob hook <event>` guards for agent harnesses; `pre-tool` invokes `grimble vet --hook` as a sibling spawn |
| frob-serve | MCP tools and the HTTP API on `gob-serve`; embeds the GUI SPA (cli-contract.md); Milestone 2 or later (D36) |
| frob (bin) | thin |

#### 4.2.3 grimble (structural and design linting)

Every grimble crate is Milestone 2 or later (D36).

| Crate | Capabilities |
|---|---|
| grimble-model | `.grmb` parser with spans, multi-file modules, typed attrs, selectors (`owns`, `surface`, `at`), flows with producer/consumer/contract, boundaries, claims, V-model, exceptions (the four kinds), JSON export |
| grimble-kernel | label closure, SCC longest-path age, demand and capacity, V-model closure, claim verdicts with witnesses, assumes with expiry |
| grimble-bind | model-to-symbol resolution, ambiguity, FOREIGN, the `binds` cross-language edge with per-`via` signature comparison, contract fingerprints, drift findings (SYS family), shrink, `grimble ack` on gob-lock |
| grimble-capabilities | capability atoms (`Capability` derive documenting entries of the gob-ir registry), per-language detectors over U, the node x capability matrix (cells per grimble/binding.md 7.5) with matrix-build template excuses, CAP family: CAP001, CAP002, CAP004 (CAP003 retired, D75; CAP005 lives in grimble-bind) and the matrix-build rule SYS012 (grimble/binding.md 6.12) |
| grimble-lints | universal rules over U (sort in loop, network in retry loop, secret literal, ...), the NEAT family (grimble/rule-families.md), language-specific structural rules (tree-sitter queries or ast-grep patterns), GPOL user policy over code; callee vocabularies are views over the gob-ir registry |
| grimble-verdict | the `Verdict` a grimble rule pass returns before the product interns its span (rule, severity, file, byte range, message, optional Unresolved reason, fingerprint anchor) and its conversion to a gob-rules `Finding`; its own crate so grimble-arch and grimble-ci share it without depending on each other | grimble-arch, grimble-ci |
| grimble-ci | the CI and DK families (grimble/rule-families.md) over the GitHub Actions and Dockerfile adapters, CI012 consistency joins through the F2 manifest adapter (grimble/grmb-spec.md 20.2) |
| grimble-arch | metrics core (size, nesting, LCOM, coupling), layering contracts, CYCLE, DEAD, LARGE, dup rungs R1-R5 |
| grimble-security | SEC and PII structural patterns, secrets, CVE fingerprints as a data pack |
| grimble-vet | dependency vetting: lockfile allowlist, advisories (OSV, RustSec), typosquat, install-script and capability scan of dependencies, delta-only mode, `vet --hook` pre-install mode that `frob hook pre-tool` invokes |
| grimble-packs | data packs: threat obligations, reliability markers, compliance views, PII categories; pack loader and schema |
| grimble-check | grimble's own `check`, `status`, `graph`, `shrink`, `init`, `packs`, `explore`; sync, no tokio |
| grimble-serve | MCP tools for design queries on gob-serve: read-only `check` and `graph` (`explore` follows once grimble has it); `launch` mints the token and announces it once on stderr (grimble-check stays free of the transport) |
| grimble (bin) | thin |

vet lives here because it is the capability model applied to
third-party code; frob's land consumes its findings like any gate.

##### 4.2.3.1 grimble vet (implemented)

Related grimble specs: [grmb-spec](../grimble/grmb-spec.md), [GRL](grl-spec.md), [capabilities v3](../grimble/grimble-capabilities-v3.md), [rule families](../grimble/rule-families.md).

Design context: cli-contract.md (`grimble vet`).

Inputs: `Cargo.lock`, the allowlist `.grimble/vet.toml` (`allow = ["serde",
"tokio@1.40.0"]`) and an offline RustSec snapshot directory (the
advisory-db layout; `--advisory-db`, default `.grimble/advisory-db`; absent
means advisories are not checked, with a warning in the log). With
`--base REF` only packages new relative to the lockfile at REF are vetted.

| Rule | Severity | Meaning |
|---|---|---|
| VET001 | error | new direct dependency not on the allowlist |
| VET002 | error | locked version has an advisory; the finding carries the id and the fixed version requirements |
| VET003 | info | new transitive dependency not on the allowlist |
| VET004 | warning | two versions of one crate are locked; a crate named (by bare name) on the allowlist is exempt, which is how a repo records duplicates it cannot avoid |

`grimble vet-refresh [SOURCE] [--db DIR] [--check] [--max-age-days N]`
maintains the snapshot: with SOURCE (an advisory-db checkout) it parses every
`RUSTSEC-*.toml`, replaces the snapshot's advisories and writes
`SNAPSHOT.toml` (`as_of` today in UTC, `count`); fetching the checkout is the
caller's job. With `--check` (or no SOURCE) it writes nothing and exits 1 when
`as_of` is missing or older than N days (default 30).

Any error exits 1. VET is a registered rule family of `grimble-check`
(`crates/grimble-vet/src/rules`), so `frob check` and `frob check --ticket`
report it natively as the `repo:vet` group, pointing at `Cargo.lock`. The
pipeline knows only error and unresolved severities, so the three
informational severities above collapse to error there; `grimble vet` keeps
them. In the pipeline VET002 and VET004 run over the head lockfile alone
(VET002 needs a snapshot in `.grimble/advisory-db`). VET001 and VET003 need a
base: `grimble check --base REF` reads
`Cargo.lock` at the merge-base of `REF` and `HEAD` and diffs against it. Without
`--base`, or when the lockfile cannot be read at the ref (logged as a warning),
they are reported as not applicable. A base where `Cargo.lock` did not exist
counts every package as new. An unparsable lockfile or allowlist is an
unresolved finding, never a silent pass.

Hook mode (library: `grimble_vet::vet_command`): vets one install-shaped
shell command (`cargo add serde`, `cargo install ripgrep@14.0.0`, also after
`&&`, `;` or `|`) before it runs. The command is parsed into registry crates
(`--git` and `--path` installs have none and are skipped); each crate off the
allowlist is VET001 and each pinned version with an advisory is VET002 (an
unpinned crate only when an advisory against it has no fix). No errors means
the command may run. The `--hook` CLI flag and the `frob hook pre-tool`
caller are separate tickets.

Snapshot refresh (library: `grimble_vet::refresh`): given an advisory-db
checkout (a clone of rustsec/advisory-db or an unpacked tarball), it parses
every `RUSTSEC-*.toml`, aborting before any write if one is invalid, then
replaces the advisory files of the snapshot directory with the source's and
writes `SNAPSHOT.toml` (`as_of`, `count`); `stamp_as_of` reads the date back.
It does no network I/O; fetching the checkout and a `grimble` verb over it are
separate tickets.

Not yet implemented: licence, yanked, maintenance and typosquat
checks (follow-up tickets).

#### 4.2.4 crunk (front-end design system)

Every crunk crate is Milestone 2 or later (D36).

Unchanged from notes/v1/crunk.md section 4: crunk-values, crunk-spec,
crunk-ingest, crunk-tailwind, crunk-rules, crunk-tokens, crunk-query,
crunk-gallery, crunk-adapters, crunk (bin). Its TS/TSX and CSS parsing
move to gob-languages and gob-symbols; its byte-range fixes move to
gob-fix; its cache to gob-cache. crunk adopts the shared exit-code
contract of docs/design/shared/cli-contract.md section 2.

#### 4.2.5 Rule family ownership

One table covers every family named in any design file. Ids are
`FAMILYNNN` with an optional slug alias in every product; the registry
namespaces families by product so a foreign family is never unknown.

| Family | Product namespace | Crate | Notes |
|---|---|---|---|
| DRIFT, AFFECT | frob | frob-obligations | ack data from frob-ack, graph from gob-symbols |
| COV, TODO, TEST, TDD, INV, DOC, DOCENUM, NEGEXIST, REF, REG, DEC, DEPR, REL, VERSION | frob | frob-obligations | accounting joins against tickets, docs, tests, releases |
| SCOPE, PRE, QUEUE | frob | frob-obligations | lease data from frob-lease |
| TICK, MILE, CROSSTICKET | frob | frob-obligations | ledger integrity, milestones, leakage |
| NARR | frob | frob-obligations | ticket narrative in comments (notes/research/documentation.md section 4) |
| POL | frob | frob-obligations | user policy over tickets and docs; `[[policy]]` in frob.toml |
| PM | frob | frob-pm | pm-and-releases.md |
| EXC001-002, EXC004, EXC006, EXC008-013, EXC016-017 | the product whose rule is excepted | gob-rules | reason checker, staleness, date expiry, budgets (EXC001 and EXC005 are emitted from frob-obligations in milestone 1, D45) |
| EXC003, EXC007, EXC014, EXC015 | frob | frob-obligations | ticket-bound exits, evaluated by frob only from sibling `--json` (3.2) |
| EXC005 | frob | frob-obligations | `accept` digest check against `frob.lock` (D45) |
| CFG | each product | gob-config detects, each product's check crate emits | CFG001, missing materialized knob |
| PARSE, DSL | the product whose file or directive is malformed | gob-directives | one id each, parametric |
| SIB | frob | frob-check | SIB001-SIB099; `sibling-unavailable`, emitted by `sibling.rs` when a configured sibling cannot be used (docs/design/shared/sibling-contract.md section 6); required Unresolved under `[check] require_siblings` |
| PACK | grimble | grimble-capabilities | PACK001-PACK099; PACK001-PACK008 of docs/design/shared/packs-and-plugins.md section 12.9; pack loading, the drift-lock and `grimble.packs.lock` |
| MDL | grimble | grimble-model | MDL000-MDL099; MDL000-MDL018 of grimble/grmb-spec.md (.grmb well-formedness) |
| FLOW | grimble | grimble-model | FLOW001-FLOW003; kernel flow findings (label closure, endorsement, rate) |
| SYS, BIND | grimble | grimble-bind | model drift and cross-language edges |
| CAP | grimble | grimble-capabilities | capability matrix; CAP001, CAP002 and CAP004 (excused but used); CAP005 (grant not acknowledged by a human, grimble-bind `grant_ack`); CAP003 is retired (D75) and its id is never reused |
| CYCLE, ARCH, LARGE, DEAD, DUP | grimble | grimble-arch | structure metrics |
| SEC, PII | grimble | grimble-security | structural security patterns |
| VET | grimble | grimble-vet | dependency vetting |
| NEAT | grimble | grimble-lints | neatness (grimble/rule-families.md); NEAT001-NEAT037; knobs in `grimble.toml` `[neat]`; tool-bound NEAT findings arrive through frob's `[[check.tool]]` stages |
| CI, DK | grimble | grimble-ci | CI001-CI015 and DK001-DK004 (grimble/rule-families.md); knobs in `grimble.toml` `[ci]`; adapters in gob-languages (features `actions`, `dockerfile`) and gob-symbols; CI012 reads manifests through the F2 manifest adapter; frob adopts zizmor and actionlint through `[[check.tool]]` before the adapters exist |
| GPOL | grimble | grimble-lints | user policy over code; `rules/*.grl.toml` next to grimble.toml and `[[policy]]` in grimble.toml |
| PATH | grimble | grimble-lints | host-path portability, PATH001-PATH003 (docs/design/shared/rules.md section 3.1, D86); GRL rules in the standard pack; knobs in `grimble.toml` `[path]` |
| TIME | grimble | grimble-lints | time and zone discipline, TIME001-TIME003 (docs/design/shared/rules.md section 3.2, D93); GRL rules in the standard pack; knobs in `grimble.toml` `[time]` |
| ERR, TESTQ, PAIR, TYPING | grimble | grimble-lints | ERR001-ERR003, TESTQ001-TESTQ003, PAIR001, TYPING001 and TYPING004 (docs/design/shared/rules.md section 3); universal over U; TYPING is not TYPE (crunk typography) |
| VIS | grimble | grimble-arch | VIS001 visibility wider than its uses |
| FMT, SPELL | frob | frob-check (registry), parsers in gob-check | bound only: formatter check mode and typos through `[[check.tool]]`; the v1 FMT001/FMT002 ids were folded into PARSE and must not alias the new FMT001 |
| NAME, LINT | grimble | grimble-lints (registry), parsers in gob-check | bound only: LINT 0xx idiom, 1xx perf idiom, 2xx correctness, 3xx concurrency, 5xx leftover debug; bound perf is LINT1xx because PERF001 is engine timing |
| REACT | grimble | grimble web pack (id map is pack content) | bound only: react-hooks and eslint-plugin-react |
| UNITY | grimble | unity pack; own rules in grimble-lints | UNITY0xx .meta/GUID, UNITY1xx bound Unity analyzers, UNITY2xx hot-context, UNITY3xx input and physics (code-model.md) |
| COLOR, SPACE, TYPE, RADIUS, SIZE, LAYER, CONTRAST, ORG, TW, BP | crunk | crunk-rules | notes/v1/crunk.md section 4 |
| A11Y, SEO, LAUNCH, WEBPERF (markup and assets) | crunk | crunk pack crunk-web | D88/D89: front-end web lint moved from v1 frob; v1 catalog in notes/v1/gates-and-rules.md section 11 |
| WEBSEC (into SEC), SQL, COMPLY (with PII), ROUTE, WEBPERF (server); STORE, SYSDESIGN, GRAMMAR | grimble | grimble packs grimble-websec and grimble-sysdesign | D89: code, data and system-design lint moved from v1 frob; v1 catalog section 11 and v1 backlog clusters B1-B2 |
| GALLERY | crunk | crunk-gallery | gallery checks |
| GEN | this repo only | not a registry family | `cargo dev gen --check` runs as a `[[check.tool]]` stage in this repo's frob.toml; its output maps to GEN001 |
| PROC and the layering rules | this repo only | gob-dev | repo-internal rules over Cargo metadata; not shipped |

Policy files live next to the owning product's config: frob's `POL`
rules in `frob.toml`, grimble's `GPOL` rules in `rules/*.grl.toml` beside
`grimble.toml`. The two prefixes cannot collide.

##### 4.2.5.1 Rule code reads the snapshot, not the disk

Rule and check code in `gob-check`, `gob-rules`, `frob-check`,
`grimble-check` and `crunk-check` reads walked files through
`gob_check::Core::text` / `Core::bytes` (git-normalized content, the same
form the walk digests), never `std::fs::read`, `read_to_string`,
`read_dir` or `File::open` (audit M7). Each of the five crates carries its
own `clippy.toml` (clippy reads only the nearest one; keep it in sync with
the workspace file) listing those methods under `disallowed-methods`, so
`cargo clippy -D warnings` rejects a new disk read. A site that is
legitimately not a walked file (configuration, caches, state dirs,
spec-declared paths, tests) carries `#[allow(clippy::disallowed_methods,
reason = "...")]`.

#### 4.2.6 v1 KEEP items and deferred items

Every item from the v1 inventories that had no owner now has one, or is
recorded as dropped with a reason.

| Item | Owner or disposition |
|---|---|
| `ticket done-report` | frob-evidence, `frob ticket done-report`; composed at close and land |
| `ticket tokens` | folded from `cost` events (frob/tickets.md section 2.4); the producer is frob-hook, Milestone 2 or later (D36) |
| `runs-last` for milestone tails, MILE001-004 | frob-obligations (MILE); Milestone 2 or later (D36) |
| `worktree sweep` and `remove` | frob-worktree; Milestone 2 or later (D36) |
| `clean` | gob-cache, `frob clean`; Milestone 2 or later (D36) |
| `verify dispose`, flake quarantine | dropped: they belong to deferred verification and `[land] verify = "ci"` (docs/design/shared/rules.md section 6), Milestone 2 or later (D36) |
| `ci_validity` (CI evidence staleness through affects) | frob-gh; Milestone 2 or later (D36) |
| scaffold templates | dropped for the product; `cargo dev scaffold-rule` is dev-only in gob-dev |
| tool-output parse library | frob-check (parsers for `[[check.tool]]`); Milestone 2 or later (D36) |
| JUnit emitter | gob-diagnostics; Milestone 2 or later (D36) |
| LSP and SCIP consumption, PyO3 leaf crate | deferred, no crate yet; Milestone 2 or later (D36) |

### 4.3 Boundary cases decided

#### 4.3.1 Invariants and decisions

`invariants/` and `docs/decisions/` are frob: they are claims about the
code that tickets and tests must honour (INV001 evidence, DEC001
implemented). The structural half of an invariant (`no_import` between
modules) is evaluated with gob-symbols import edges inside frob; it does
not need the architecture model. If a repo wants layering as a design
fact it declares flows in grimble; the two can coexist and PM rules do
not know about grimble (PM026 uses the gob-symbols public-API graph
only).

#### 4.3.2 Exceptions and ratchets

Mechanism in gob-rules (one matcher, one reason checker, one pool file
per product: `frob-ratchet.lock.json`, `grimble-ratchet.lock.json`) over
the grammar in gob-directives. Hygiene rules about exceptions fire under
the product whose rule is excepted. Exceptions whose exit names a ticket
(`defer`, `hotfix`) and the close guard are evaluated by frob only:
grimble and crunk parse such an exception, treat `ticket=` as opaque and
emit it in their `--json`; frob's orchestrated check reads that JSON to
decide EXPIRED and to block closing a ticket a defer still points at.
Standalone grimble or crunk reports such an exception as UnresolvedExit (an exception state, not the Unresolved severity).
The `.grmb` language uses the same four kinds (grimble/grmb-spec.md 20 section
2). Ack mechanics live in gob-lock: `frob.lock` for frob and
`grimble.lock` for grimble, each with its own `ack` verb. The audit view
(`frob exceptions`) is frob.

#### 4.3.3 Code exploration verbs

`outline`, `map`, `xref`, `graph query/affects` are gob-symbols views.
Both binaries expose them (`frob explore ...` through frob-explore,
`grimble explore ...` through grimble-check) because an agent working
tickets and a human reviewing architecture both want them and should not
need the other binary. `why` (acks) is frob only; `status` exists in
each product with its own meaning (frob: work and exceptions; grimble:
model drift).

#### 4.3.4 Tests and coverage

Touched-set selection and evidence are frob; they exist to prove work.
grimble never runs tests.

#### 4.3.5 Docs

Doc anchors and `describes` are frob (claims about code). Generated
docs for rules and CLI are gob-dev for all products (documentation.md
section 4.3); changelog compilation is frob-release, which gob-dev calls.

#### 4.3.6 Release

frob. The public-API graph query (used for semver inference and PM026)
lives in gob-symbols so frob does not depend on grimble.

#### 4.3.7 Policy rules written by users

Policy over code (tree-sitter queries, patterns over U) is grimble: `GPOL`
rules in `rules/*.grl.toml` next to `grimble.toml`. Policy over tickets
and docs (for example "every security ticket needs a threat field") is
frob: `POL` rules under `[[policy]]` in `frob.toml`. Both compile into
gob-rules at load time and use distinct prefixes.

#### 4.3.8 Hooks and agent harness guards

frob-hook, because the guards are about tickets, scope, and directive
hygiene. grimble ships no hook binary; its `vet --hook` mode is invoked
by `frob hook pre-tool` as a sibling spawn.

#### 4.3.9 grimble data that frob consumes

frob reads grimble entities and `binds` edges only through
`grimble --json` (checked `schema_version`; a configured grimble that is
absent is a required Unresolved, docs/design/shared/cli-contract.md section 2). `binds` directives are the `grimble:` namespace and are
resolved in grimble-bind; frob never parses them. A ticket `implements`
link to a `design:` entity, and frob's evidence reach across a `binds`
edge, therefore use the exported entity and edge lists. The capability
census is `grimble check --census capabilities`.

### 4.4 More splits considered

| Candidate split | Verdict | Reason |
|---|---|---|
| a fourth binary for code exploration (outline, xref, graph) | no | views over gob-symbols, cheap to expose from both; a fourth install for navigation is not worth it, LSPs already cover navigation |
| grimble-model as its own product (design language without lints) | no | docs/design/shared/charter.md section 2: half the lints need the model and the model is useless without the code graph |
| vet as its own binary | no | it is capability detection on dependencies; same detectors, same matrix; `grimble vet` gives the standalone use |
| frob-pm as its own product (planning without enforcement) | no | planning that cannot be checked is Jira; the value is the join with leases, evidence, and landing |
| the GUI as its own binary | no | stateless over frob's handlers; it ships inside frob-serve |
| server runtime (MCP, HTTP) shared as gob-serve | yes, small | transport plumbing (rmcp setup, JSON envelope over HTTP, SSE) is identical; tools and routes stay per product |
| the former single syntax crate split into gob-symbols (identity, digests, imports, call graph, public-API graph) and gob-ir (the universal model) | yes, revised by D56 | frob needs imports and the call graph (AFFECT, COV private-reach, touched-set tests, INV forbidden-import, semver), so they live in gob-symbols; gob-ir sits below gob-symbols (the adapters produce U terms) and frob links it from milestone 2 for digests, polarity and the CI adapters, so the earlier claim that gob-ir stays out of frob's build no longer holds |
| gob-languages per language family crates | yes (already in code-model.md) | feature-gated grammar crates keep C builds local |
| gob-git split into read snapshot and write transaction | no | one crate, two modules; the spawn registry must see both |
| ack mechanics inside frob-ack only | no | grimble needs drift acks; they move to gob-lock with one file per product |

Net: additions are gob-serve, gob-ir (the universal model, below
gob-symbols), gob-lock, gob-check, gob-pattern, grimble-serve and
grimble-ci; gob-db (salsa) is a milestone-2 crate. No new products.
Three binaries, 24 substrate crates (gob-dev included), 17 frob crates (frob-docgen, the generator binary that links frob for gob-dev, included),
13 grimble crates, 13 crunk crates. Each crate builds and tests alone.

### 4.5 Naming

- Substrate prefix `gob-` (the shared goblin substrate) rather than
  `core-` or `frob-`: short, product-neutral, and grep-able. Decided by
  the owner 2026-10-02.
- Product crates carry the product prefix and a noun for the
  capability (`frob-ledger`, `grimble-bind`, `crunk-tokens`), never a
  verb or a layer name (`-utils`, `-common` are banned by a repo rule).
- Rule ids are `FAMILYNNN` with an optional slug alias in every product.
  Families are namespaced in the registry by product so `COLOR001`
  (crunk) and `COV001` (frob) cannot collide; PARSE and DSL are emitted
  under the namespace of the product that parsed the file.

### 4.6 Dependency rules (enforced by a repo-internal rule over Cargo metadata)

- `gob-*` depends only on `gob-*`. Substrate order from milestone 2:
  gob-text and gob-macros at the bottom, then gob-languages, then
  gob-ir, then gob-symbols, then gob-directives; gob-rules uses the
  answer lattice from gob-ir.
- `frob-*`, `grimble-*`, `crunk-*` depend on `gob-*` and on their own
  product's crates; never on another product's crates.
- The one exception: the `frob` binary with feature `bundle` also
  depends on `grimble-check` and crunk's check crate to run them
  in-process. Consequences, stated rather than hidden: frob releases
  pin the bundled grimble and crunk crate versions in lockstep; a build
  without `bundle` (for example crates.io `frob-cli`) behaves the same
  except that a configured sibling it cannot run is an Unresolved
  finding (required under the default `[check] fail_on_unresolved`,
  exit 1; docs/design/shared/cli-contract.md section 2), never a silent omission; and sibling
  `--json` output carries `schema_version`, which frob checks, treating
  a mismatch as an incompatible sibling (the same required Unresolved).
- Only `gob-exec` references `std::process`; gob-git and every other
  crate spawn through it.
- Only `gob-serve`, `frob-serve`, `grimble-serve` and `frob-gh` use
  tokio.

<!-- frob:ticket 01M4CTE1SS9RQ0JB8BNCJXZJ2V -->

#### 4.6.1 Layer table

`crates/gob-dev/tests/layering.rs` reads this table and walks the
normal and build dependencies from `cargo metadata`. A crate may depend
only on crates in a strictly lower layer, and on its own product or
`gob-*` (a `gob-*` crate on `gob-*` only). A new edge that breaks either
rule fails the test and names both crates and their layers. The few
edges that break the table today are listed in the test with the ticket
that removes each; fixing one makes its row stale, and the stale row
fails the test. Every workspace crate must appear here exactly once.

| Layer | Name | Crates |
|---|---|---|
| 0 | foundation | gob-path, gob-term |
| 1 | base | crunk-values, frob-present, gob-caps, gob-fs, gob-log, gob-macros, gob-text, gob-time |
| 2 | io | gob-exec, gob-languages, gob-lock, gob-walk |
| 3 | repo | gob-git, gob-trust |
| 4 | model | gob-cache, gob-ir |
| 5 | rules | gob-pattern, gob-rules, gob-symbols |
| 6 | config | crunk-scene, gob-config, gob-diagnostics, gob-fix, gob-frameworks, gob-plan |
| 7 | pipeline | crunk-layout, frob-doc, gob-check, gob-cli, gob-directives, gob-mdtest, gob-packs, gob-serve, gob-testsupport |
| 8 | product base | crunk-spec, crunk-tailwind, frob-ack, frob-ledger, gob-product, grimble-capabilities, grimble-lints, grimble-model, grimble-verdict |
| 9 | product core | crunk-gallery, crunk-ingest, crunk-tokens, frob-lease, frob-mirror, frob-pm, grimble-bind, grimble-vet |
| 10 | product mid | crunk-query, crunk-rules, frob-metrics, frob-release, frob-worktree, grimble-arch |
| 11 | product upper | crunk-check, frob-evidence, frob-gh, grimble-ci |
| 12 | product top | crunk-fix, frob-tests, grimble-check |
| 13 | product serve | grimble-serve |
| 14 | product apex | crunk, grimble |
| 15 | obligations | frob-obligations |
| 16 | check | frob-check |
| 17 | land | frob-land |
| 18 | binary | frob-cli |
| 19 | tool | gob-dev |
| 20 | docgen | frob-docgen |

## Decision records

The decisions homed here, moved from the old design/README.md log. The index is [docs/decisions/README.md](../../decisions/README.md), generated from decisions.toml.

### D2

ULID ticket ids; no counters, drafts, promote, renumber

### D4

Two-tier rules: universal over the universal structural model U (the earlier "structural IR" is superseded by D56), language-specific over tree-sitter

### D11

Three products: frob (work accounting), grimble (structure and architecture model, .grmb files), crunk (front-end design system); structural lints and the design model are one tool

### D87

Owner decision 2026-10-03: one binary per package, composed by dependencies. PyPI ships `frob`, `grimble` and (once the Rust crunk ships here) `crunk` as separate projects of prebuilt wheels, each carrying only its own binary; `frob` depends on the other two pinned to the same version, so one install still gets all three without duplicate executables; frob finds siblings next to its own executable first, then on PATH; crates.io carries the source crates; each PyPI project trusts this repository's `release.yml` with environment `pypi`; lognd/crunk stays a second crunk publisher until the Rust crunk ships

### D97

Coordinator decision 2026-10-06 (owner: "You can make the abstractions"): one product front end. `gob-check::sibling` owns the gob.sibling/1 emitter and parser; a new crate gob-product holds the `Product` trait and the generic check, doctor and workspace verbs that the crunk and grimble binaries (and frob's check and doctor) instantiate; products register generated artifacts through inventory instead of gob-dev calling them by name

### D9

frob, grimble and crunk share one workspace with `gob-*` substrate crates

### D22

Owner decisions 2026-10-02: `gob-` prefix, repo stays `frob`, everything MIT, ULID-only ids, no large blobs in the repo, error_set trial, declarative ast-grep-shaped rules, SARIF inside 2.0, `.grmb` is its own language, no invisible variables, doc lints as errors from day one; crates.io package `frob-cli`

### D35

Publishing (audit M19): crates.io receives the full crate set at release in lockstep versions because `frob-cli` depends on them; binaries ship via cargo-dist and PyPI; names are reserved at first publish

### D18

Substrate crates are `gob-*`; products never depend on each other (the `bundle` feature is the one stated exception); grimble and crunk are standalone binaries frob can orchestrate

### D31

Crate split (audit M1): imports and the call graph live in gob-symbols; gob-ir holds only the structural IR (superseded by D56: gob-ir is below gob-symbols); gob-db (salsa) is a milestone-2 crate

### D63

Layering and owners: gob-languages < gob-ir < gob-symbols < gob-directives < frob and grimble crates; NEAT (grimble-lints), CI and DK (new crate grimble-ci) are grimble families, with the Actions and Dockerfile adapters in gob-languages behind features `actions` and `dockerfile`; claim directives (`grimble:effects` and the rest, namespaced by consumer per D120) are `grimble:` verbs evaluated by NEAT; one open capability and atom registry in gob-ir with a sixth `not-applicable` matrix cell
