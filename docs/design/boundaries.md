# Boundaries: what belongs to frob, grimble, crunk, and the shared substrate

Status: current
Owner: gob
Decisions: none
Audience: contributor

Provenance: written under T-0001 (a v1-format id that migrates with an alias).
Supersedes the crate list in architecture.md section 1 and refines
products.md. Owner question 2026-10-02: where exactly do the boundaries
sit, is grimble a standalone binary, should there be more splits, and
are the crates named right?

## 1. The placement test

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
stages that feed them (section 2.5).

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
(cli.md section 2 is the one definition), so a check never silently
omits a family. grimble and crunk never call frob.

## 2. Capability map

Every capability named in the other design files and the v1 inventories.

### 2.1 Substrate crates (`gob-*`, library only except `gob-dev`)

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
| gob-diagnostics | renderers: text with remedy, JSON envelope, GitHub annotations, SARIF and JUnit (Milestone 2 or later (D36)); the exit-code contract of cli.md section 2, shared by all three binaries | one output contract |
| gob-fix | Edit, Fix with tiers A/B/C, overlap resolution, dry-run diff, atomic write, fix journal | frob gates, grimble lints, crunk token rewrites all fix |
| gob-walk | file discovery over `ignore`, globset, selectors (`path::qual` globs) | scope leases, owns selectors, crunk globs |
| gob-cache | SQLite store per worktree keyed by content, parser identity, schema version; findings table; `busy_timeout`, best-effort writes, WAL readers | parse artifacts, findings, ticket index, crunk cache |
| gob-git | gix repository handle, snapshot of HEAD/status/diff/worktrees, ledger commit and CAS ref writes (git-io.md); every spawn goes through gob-exec | frob (ledger, land), grimble and crunk (diff-scoped checks) |
| gob-exec | the only crate that references `std::process`: bounded job pool, timeouts, env scrubbing, output caps with redaction, spawn registry and counter | test runners, external linters, Tailwind helper, git fallbacks, siblings |
| gob-lock | lock file format (typed entries, `digest_scheme`), ack mechanics and the ack planner, one file per product (`frob.lock`, `grimble.lock`), the shared `ack` implementation | frob acks, grimble drift acks |
| gob-cli | clap conventions: global flags, `--json/--text/--schema`, did-you-mean, completions, help generation, `schema` | identical surface in three binaries |
| gob-log | tracing subscriber setup, telemetry record, redaction, `--timing` span tree | one observability story |
| gob-serve | MCP and HTTP transport plumbing on tokio (rmcp setup, JSON envelope over HTTP, SSE, token and Origin checks) | tools and routes stay per product |
| gob-mdtest | markdown corpus harness over datatest-stable | rule tests in every product |
| gob-check | the product-neutral check pipeline: snapshot core, file and repo rule caches, `--only` with known sibling families, exception application, render (milestone 2, ticket G06; grimble-model.md 9.7) | `frob check` and `grimble check` run one pipeline |
| gob-pattern | the pattern engine for declarative rules: ast-grep shape at grammar level and over U roles (milestone 2, ticket G17, blocked by the `Doc`-over-U spike of rules.md section 3) | GPOL and NEAT-style rule files in every product |
| gob-dev | the `cargo dev` binary (never shipped): `cargo dev gen` for every product (rule docs, CLI docs, schemas, config docs, TS types; it calls frob-release for the changelog), repo-internal rules (PROC, dependency layering) | one generator |

### 2.2 frob (project management and work accounting)

| Crate | Capabilities |
|---|---|
| frob-ledger | ticket files, ULID ids and handle resolution, `TicketSchema` schema, events, comments, links with topology, custom fields, index, query language, merge driver, `migrate` from v1 |
| frob-pm | types and hierarchy requirements, structured stories, definitions of ready/done, cycles, velocity, capacity checks, forecasts (Monte Carlo, Little's law), flow metrics, WIP limits, `stats`, PM rule family; Milestone 2 or later (D36) |
| frob-lease | scope leases in `.git/frob/leases` taken under one lock file, overlap on glob intersection or resolved file sets (symbol sets and append mode: Milestone 2 or later (D36)), TTL and heartbeat, steal, doable, wave, contention |
| frob-worktree | `work`: worktree create or reuse (path convention in cli.md section 3), merge of main, start; `worktree sweep` and `remove`, reconcile |
| frob-evidence | evidence providers (pytest, cargo test, ctest, vitest, junit, command), verdicts, acceptance binding, repro-at-parent, done-report composition |
| frob-tests | touched-set selection from the gob-symbols graph and the diff, runner templates per language, coverage stamp |
| frob-obligations | the accounting rule families of section 2.5 (DRIFT through NARR and POL), and the ticket-bound exception exits EXC003 and EXC007 with the close guard (EXC005, the accept digest check, is emitted here too in milestone 1) |
| frob-ack | `frob.lock` symbol entries (format, mechanics and, from ticket G05, the ack planner in gob-lock), acks with reasons, stale and dangling detection, rename candidates, `why` and `affects` views |
| frob-land | the land transaction, CAS publish, passenger detection, deletion filter, LAND-PROOF, the land lock and `--wait <secs>` (no jobs) |
| frob-release | release objects, version authority, changelog fragments and `frob release changelog` compilation, semver from the gob-symbols public-API graph, stamp, publish |
| frob-fleet | fleet manifest, cross-repo status and routing; Milestone 2 or later (D36) |
| frob-explore | outline, map, xref, docs search, graph query (thin views over gob-symbols; also exposed by grimble, see 3.3) |
| frob-check | orchestration of frob's families plus sibling products over gob-check, selection, `--ticket` scoping, tool-output parsers and id maps for `[[check.tool]]`, `status` |
| frob-gh | GitHub over HTTPS: PR for a land, CI status, releases, issue import (Milestone 2 or later (D36)) |
| frob-hook | `frob hook <event>` guards for agent harnesses; `pre-tool` invokes `grimble vet --hook` as a sibling spawn |
| frob-serve | MCP tools and the HTTP API on `gob-serve`; embeds the GUI SPA (gui.md); Milestone 2 or later (D36) |
| frob (bin) | thin |

### 2.3 grimble (structural and design linting)

Every grimble crate is Milestone 2 or later (D36).

| Crate | Capabilities |
|---|---|
| grimble-model | `.grmb` parser with spans, multi-file modules, typed attrs, selectors (`owns`, `surface`, `at`), flows with producer/consumer/contract, boundaries, claims, V-model, exceptions (the four kinds), JSON export |
| grimble-kernel | label closure, SCC longest-path age, demand and capacity, V-model closure, claim verdicts with witnesses, assumes with expiry |
| grimble-bind | model-to-symbol resolution, ambiguity, FOREIGN, the `binds` cross-language edge with per-`via` signature comparison, contract fingerprints, drift findings (SYS family), shrink, `grimble ack` on gob-lock |
| grimble-capabilities | capability atoms (`Capability` derive documenting entries of the gob-ir registry), per-language detectors over U, the node x capability matrix (cells per grimble-model.md 9.6) with matrix-build template excuses, CAP family: CAP001, CAP002, CAP004 (CAP003 retired, D75) and the matrix-build rule SYS012 (binding.md 6.12) |
| grimble-lints | universal rules over U (sort in loop, network in retry loop, secret literal, ...), the NEAT family (neatness.md), language-specific structural rules (tree-sitter queries or ast-grep patterns), GPOL user policy over code; callee vocabularies are views over the gob-ir registry |
| grimble-ci | the CI and DK families (cicd.md) over the GitHub Actions and Dockerfile adapters, CI012 consistency joins through the F2 manifest adapter (grimble-model.md 9.8) |
| grimble-arch | metrics core (size, nesting, LCOM, coupling), layering contracts, CYCLE, DEAD, LARGE, dup rungs R1-R5 |
| grimble-security | SEC and PII structural patterns, secrets, CVE fingerprints as a data pack |
| grimble-vet | dependency vetting: lockfile allowlist, advisories (OSV, RustSec), typosquat, install-script and capability scan of dependencies, delta-only mode, `vet --hook` pre-install mode that `frob hook pre-tool` invokes |
| grimble-packs | data packs: threat obligations, reliability markers, compliance views, PII categories; pack loader and schema |
| grimble-check | grimble's own `check`, `status`, `graph`, `shrink`, `init`, `packs`, `explore`; sync, no tokio |
| grimble-serve | MCP tools for design queries on gob-serve (tokio stays out of grimble-check) |
| grimble (bin) | thin |

vet lives here because it is the capability model applied to
third-party code; frob's land consumes its findings like any gate.

### 2.4 crunk (front-end design system)

Every crunk crate is Milestone 2 or later (D36).

Unchanged from notes/crunk.md section 4: crunk-values, crunk-spec,
crunk-ingest, crunk-tailwind, crunk-rules, crunk-tokens, crunk-query,
crunk-gallery, crunk-adapters, crunk (bin). Its TS/TSX and CSS parsing
move to gob-languages and gob-symbols; its byte-range fixes move to
gob-fix; its cache to gob-cache. crunk adopts the shared exit-code
contract of cli.md section 2.

### 2.5 Rule family ownership

One table covers every family named in any design file. Ids are
`FAMILYNNN` with an optional slug alias in every product; the registry
namespaces families by product so a foreign family is never unknown.

| Family | Product namespace | Crate | Notes |
|---|---|---|---|
| DRIFT, AFFECT | frob | frob-obligations | ack data from frob-ack, graph from gob-symbols |
| COV, TODO, TEST, TDD, INV, DOC, DOCENUM, NEGEXIST, REF, REG, DEC, DEPR, REL, VERSION | frob | frob-obligations | accounting joins against tickets, docs, tests, releases |
| SCOPE, PRE, QUEUE | frob | frob-obligations | lease data from frob-lease |
| TICK, MILE, CROSSTICKET | frob | frob-obligations | ledger integrity, milestones, leakage |
| NARR | frob | frob-obligations | ticket narrative in comments (documentation.md section 4) |
| POL | frob | frob-obligations | user policy over tickets and docs; `[[policy]]` in frob.toml |
| PM | frob | frob-pm | pm-enforcement.md |
| EXC001-002, EXC004, EXC006, EXC008-013, EXC016-017 | the product whose rule is excepted | gob-rules | reason checker, staleness, date expiry, budgets (EXC001 and EXC005 are emitted from frob-obligations in milestone 1, D45) |
| EXC003, EXC007, EXC014, EXC015 | frob | frob-obligations | ticket-bound exits, evaluated by frob only from sibling `--json` (3.2) |
| EXC005 | frob | frob-obligations | `accept` digest check against `frob.lock` (D45) |
| CFG | each product | gob-config detects, each product's check crate emits | CFG001, missing materialized knob |
| PARSE, DSL | the product whose file or directive is malformed | gob-directives | one id each, parametric |
| SIB | frob | frob-check | SIB001-SIB099; `sibling-unavailable`, emitted by `sibling.rs` when a configured sibling cannot be used (sibling-contract.md section 6); required Unresolved under `[check] require_siblings` |
| PACK | grimble | grimble-capabilities | PACK001-PACK099; PACK001-PACK008 of packs.md section 9; pack loading, the drift-lock and `grimble.packs.lock` |
| MDL | grimble | grimble-model | MDL000-MDL099; MDL000-MDL018 of grmb-spec.md (.grmb well-formedness) |
| SYS, BIND | grimble | grimble-bind | model drift and cross-language edges |
| CAP | grimble | grimble-capabilities | capability matrix; CAP001, CAP002 and CAP004 (excused but used); CAP003 is retired (D75) and its id is never reused |
| CYCLE, ARCH, LARGE, DEAD, DUP | grimble | grimble-arch | structure metrics |
| SEC, PII | grimble | grimble-security | structural security patterns |
| VET | grimble | grimble-vet | dependency vetting |
| NEAT | grimble | grimble-lints | neatness (neatness.md); NEAT001-NEAT037; knobs in `grimble.toml` `[neat]`; tool-bound NEAT findings arrive through frob's `[[check.tool]]` stages |
| CI, DK | grimble | grimble-ci | CI001-CI015 and DK001-DK004 (cicd.md); knobs in `grimble.toml` `[ci]`; adapters in gob-languages (features `actions`, `dockerfile`) and gob-symbols; CI012 reads manifests through the F2 manifest adapter; frob adopts zizmor and actionlint through `[[check.tool]]` before the adapters exist |
| GPOL | grimble | grimble-lints | user policy over code; `rules/*.grl.toml` next to grimble.toml and `[[policy]]` in grimble.toml |
| PATH | grimble | grimble-lints | host-path portability, PATH001-PATH003 (rules.md section 3.1, D86); GRL rules in the standard pack; knobs in `grimble.toml` `[path]` |
| TIME | grimble | grimble-lints | time and zone discipline, TIME001-TIME003 (rules.md section 3.2, D93); GRL rules in the standard pack; knobs in `grimble.toml` `[time]` |
| COLOR, SPACE, TYPE, RADIUS, SIZE, LAYER, CONTRAST, ORG, TW, BP | crunk | crunk-rules | notes/crunk.md section 4 |
| A11Y, SEO, LAUNCH, WEBPERF (markup and assets) | crunk | crunk pack crunk-web | D88/D89: front-end web lint moved from v1 frob; v1 catalog in notes/v1/gates-and-rules.md section 11 |
| WEBSEC (into SEC), SQL, COMPLY (with PII), ROUTE, WEBPERF (server); STORE, SYSDESIGN, GRAMMAR | grimble | grimble packs grimble-websec and grimble-sysdesign | D89: code, data and system-design lint moved from v1 frob; v1 catalog section 11 and v1 backlog clusters B1-B2 |
| GALLERY | crunk | crunk-gallery | gallery checks |
| GEN | this repo only | not a registry family | `cargo dev gen --check` runs as a `[[check.tool]]` stage in this repo's frob.toml; its output maps to GEN001 |
| PROC and the layering rules | this repo only | gob-dev | repo-internal rules over Cargo metadata; not shipped |

Policy files live next to the owning product's config: frob's `POL`
rules in `frob.toml`, grimble's `GPOL` rules in `rules/*.grl.toml` beside
`grimble.toml`. The two prefixes cannot collide.

### 2.6 v1 KEEP items and deferred items

Every item from the v1 inventories that had no owner now has one, or is
recorded as dropped with a reason.

| Item | Owner or disposition |
|---|---|
| `ticket done-report` | frob-evidence, `frob ticket done-report`; composed at close and land |
| `ticket tokens` | folded from `cost` events (tickets.md section 2a); the producer is frob-hook, Milestone 2 or later (D36) |
| `runs-last` for milestone tails, MILE001-004 | frob-obligations (MILE); Milestone 2 or later (D36) |
| `worktree sweep` and `remove` | frob-worktree; Milestone 2 or later (D36) |
| `clean` | gob-cache, `frob clean`; Milestone 2 or later (D36) |
| `verify dispose`, flake quarantine | dropped: they belong to deferred verification and `[land] verify = "ci"` (rules.md section 6), Milestone 2 or later (D36) |
| `ci_validity` (CI evidence staleness through affects) | frob-gh; Milestone 2 or later (D36) |
| scaffold templates | dropped for the product; `cargo dev scaffold-rule` is dev-only in gob-dev |
| tool-output parse library | frob-check (parsers for `[[check.tool]]`); Milestone 2 or later (D36) |
| JUnit emitter | gob-diagnostics; Milestone 2 or later (D36) |
| LSP and SCIP consumption, PyO3 leaf crate | deferred, no crate yet; Milestone 2 or later (D36) |

## 3. Boundary cases decided

### 3.1 Invariants and decisions

`invariants/` and `docs/decisions/` are frob: they are claims about the
code that tickets and tests must honour (INV001 evidence, DEC001
implemented). The structural half of an invariant (`no_import` between
modules) is evaluated with gob-symbols import edges inside frob; it does
not need the architecture model. If a repo wants layering as a design
fact it declares flows in grimble; the two can coexist and PM rules do
not know about grimble (PM026 uses the gob-symbols public-API graph
only).

### 3.2 Exceptions and ratchets

Mechanism in gob-rules (one matcher, one reason checker, one pool file
per product: `frob-ratchet.lock.json`, `grimble-ratchet.lock.json`) over
the grammar in gob-directives. Hygiene rules about exceptions fire under
the product whose rule is excepted. Exceptions whose exit names a ticket
(`defer`, `hotfix`) and the close guard are evaluated by frob only:
grimble and crunk parse such an exception, treat `ticket=` as opaque and
emit it in their `--json`; frob's orchestrated check reads that JSON to
decide EXPIRED and to block closing a ticket a defer still points at.
Standalone grimble or crunk reports such an exception as UnresolvedExit (an exception state, not the Unresolved severity).
The `.grmb` language uses the same four kinds (grimble-model.md section
2). Ack mechanics live in gob-lock: `frob.lock` for frob and
`grimble.lock` for grimble, each with its own `ack` verb. The audit view
(`frob exceptions`) is frob.

### 3.3 Code exploration verbs

`outline`, `map`, `xref`, `graph query/affects` are gob-symbols views.
Both binaries expose them (`frob explore ...` through frob-explore,
`grimble explore ...` through grimble-check) because an agent working
tickets and a human reviewing architecture both want them and should not
need the other binary. `why` (acks) is frob only; `status` exists in
each product with its own meaning (frob: work and exceptions; grimble:
model drift).

### 3.4 Tests and coverage

Touched-set selection and evidence are frob; they exist to prove work.
grimble never runs tests.

### 3.5 Docs

Doc anchors and `describes` are frob (claims about code). Generated
docs for rules and CLI are gob-dev for all products (documentation.md
section 3); changelog compilation is frob-release, which gob-dev calls.

### 3.6 Release

frob. The public-API graph query (used for semver inference and PM026)
lives in gob-symbols so frob does not depend on grimble.

### 3.7 Policy rules written by users

Policy over code (tree-sitter queries, patterns over U) is grimble: `GPOL`
rules in `rules/*.grl.toml` next to `grimble.toml`. Policy over tickets
and docs (for example "every security ticket needs a threat field") is
frob: `POL` rules under `[[policy]]` in `frob.toml`. Both compile into
gob-rules at load time and use distinct prefixes.

### 3.8 Hooks and agent harness guards

frob-hook, because the guards are about tickets, scope, and directive
hygiene. grimble ships no hook binary; its `vet --hook` mode is invoked
by `frob hook pre-tool` as a sibling spawn.

### 3.9 grimble data that frob consumes

frob reads grimble entities and `binds` edges only through
`grimble --json` (checked `schema_version`; a configured grimble that is
absent is a required Unresolved, cli.md section 2). `binds` directives are the `grimble:` namespace and are
resolved in grimble-bind; frob never parses them. A ticket `implements`
link to a `design:` entity, and frob's evidence reach across a `binds`
edge, therefore use the exported entity and edge lists. The capability
census is `grimble check --census capabilities`.

## 4. More splits considered

| Candidate split | Verdict | Reason |
|---|---|---|
| a fourth binary for code exploration (outline, xref, graph) | no | views over gob-symbols, cheap to expose from both; a fourth install for navigation is not worth it, LSPs already cover navigation |
| grimble-model as its own product (design language without lints) | no | products.md section 2: half the lints need the model and the model is useless without the code graph |
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
Three binaries, 24 substrate crates (gob-dev included), 16 frob crates,
12 grimble crates, 10 crunk crates. Each crate builds and tests alone.

## 5. Naming

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

## 6. Dependency rules (enforced by a repo-internal rule over Cargo metadata)

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
  exit 1; cli.md section 2), never a silent omission; and sibling
  `--json` output carries `schema_version`, which frob checks, treating
  a mismatch as an incompatible sibling (the same required Unresolved).
- Only `gob-exec` references `std::process`; gob-git and every other
  crate spawn through it.
- Only `gob-serve`, `frob-serve`, `grimble-serve` and `frob-gh` use
  tokio.
