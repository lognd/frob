# frob v2: goals and principles

Status: current
Owner: gob
Decisions: none
Audience: owner

Provenance: written under T-0001 (a v1-format id that migrates with an alias). This
file is the charter; the architecture lives in `architecture.md` and each
subsystem has its own file.

## One sentence

frob v2 is a fast Rust binary that is the project-management and work-
accounting layer for a repository: a git-tracked ticket ledger that
supersets Jira, enforced project-management discipline, and gates that
make unaccounted-for work a build failure. It ships from one workspace
with two sibling goblins (products.md, boundaries.md): grimble, the
structural and design linter whose `.grmb` model binds to code symbols
across languages, and crunk, the front-end design-system linter. All
three share the `gob-*` substrate crates.

## Why rewrite

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

## Goals (ranked)

1. Speed. Warm `frob check` on a 100k-line repo in under 2s ("warm" is
   a fresh process with a populated per-worktree `.frob/` cache, not a
   daemon; architecture.md section 2); any ticket read in under 50ms and
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
   (pm-enforcement.md: structured stories and quality objectives,
   definitions of ready and done, capacity-checked cycles, measured
   forecasts; cycles and forecasts are Milestone 2 or later (D36)).
7. Observability: structured `tracing` everywhere, every invocation
   recorded, every slow path explainable with `--timing`.
8. Minimal process IO: git through gix in-process, a counted short list
   of spawns, no `gh` (git-io.md); expensive steps parallel from day one
   (architecture.md section 9).

## Non-goals

- Code navigation/editing (LSP clients do that). Consuming LSP or SCIP
  data is deferred: Milestone 2 or later (D36), no crate yet.
- A hosted web service. Local-first; the optional `frob serve` (MCP and
  HTTP) is read-write behind a mandatory per-launch token (gui.md); it
  is a thin view over the same handlers, not a second code path.
- Byte-compatibility with v1 on-disk formats. A one-shot `frob migrate`
  imports v1 tickets, `frob.lock`, config, waivers, directives and
  `.strata` files (migration.md); nothing else carries.
- Python interop in the core. PyO3 bindings are an optional leaf crate:
  Milestone 2 or later (D36), no crate in boundaries.md yet.

## Principles

- Tracked text is truth; `.frob/` is a cache that may be deleted at any
  time. The only deliberate non-git state is leases, the local evidence
  artifact store and per-worktree caches, each with stated loss
  semantics (architecture.md section 3); none of it is authoritative.
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

## Ticket identity decision

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

## Requirement: universal symbolic binding and two-tier rules

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
