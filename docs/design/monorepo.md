# Monorepo: frob, grimble and crunk in one workspace

Status: current
Owner: gob
Decisions: none
Audience: contributor

Provenance: written under T-0001 (a v1-format id that migrates with an alias). Inputs: notes/crunk.md (crunk survey and its
FROBLEMS.md complaints), notes/rust-ecosystem.md section 1 (ruff/ty
layout).

## 1. Decision

One repository, one Cargo workspace, one `Cargo.lock`, three shipped
binaries (`frob`, `grimble`, `crunk`; products.md), shared `gob-*`
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

## 2. Layout

```
crates/
  gob-*             substrate (boundaries.md section 2.1)
  frob-*            project management and work accounting
  grimble-*         structural and design linting
  crunk-*           front-end design system
  frob, grimble, crunk    binaries
  gob-dev           cargo dev generator for all three (the one substrate binary, never shipped)
events/             non-ticket events (tickets.md section 2a)
docs/
  design/           this set
  frob/ grimble/ crunk/   per-product docs (generated rule and CLI pages inside)
packs/              grimble data packs
tickets/            one ledger, `component` field distinguishes products
```

Shared crates carry the `gob-` prefix (not `frob-`) so grimble and
crunk are not second-class citizens in their own code.

## 3. What the shared layer must support for grimble and crunk

- Directive namespaces: `crunk:defer`, `grimble:accept` and `frob:ticket`
  come from the same parser with a namespace parameter; a verb belongs
  to the product that consumes it, and a repo declares which namespaces
  it honours in `[directives] namespaces` (architecture.md section 6).
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

## 4. Release and CI

- One lockstep version for every crate and binary (releases.md 5, D83);
  per-binary tags `frob-v*`, `grimble-v*`, `crunk-v*` at the same commit
  for the binaries that ship in a release; cargo-dist per binary.
  crates.io receives the full crate set at release, in lockstep versions, because `frob-cli` depends on
  every `gob-*` and `frob-*` crate it links (D35); binaries also ship
  through cargo-dist and PyPI. Package names are reserved at first
  publish (products.md section 5).
- Path-filtered CI jobs: a product's crates run that product's tests;
  `crates/gob-*` changes run all three; `crates/frob-*` also runs the
  self-check. One `cargo dev gen --check` covers all three products.
- One ticket ledger. Tickets carry `component = "frob" | "grimble" |
  "crunk" | "gob"`; `frob ticket doable --component crunk` filters. Scope leases
  are path-based so the products rarely contend; `gob-*` tickets
  are the shared hot zone and get the append-mode lease (tickets.md,
  Milestone 2 or later (D36)).

## 5. Migration order

Milestone 1 (D36): frob checks and lands in this repository with the
Rust, markdown and TOML adapters only; the crate cut is the table at the
end of notes/audit-design.md. Steps 2 to 4 below, and everything about
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
3. crunk v2 crates are built against `gob-*`; crunk v1 (Python) stays
   released from its own repo until crunk v2 passes crunk's existing
   system tests (1158 tests; the markdown corpora port first).
4. crunk repo archived; its ticket history imported with `frob migrate
   tickets --from ../crunk --component crunk`, with aliases namespaced by
   source repo (`crunk:T-0042`) so they cannot collide with frob's own
   `T-0042` (migration.md).

## 6. Decided (2026-10-02)

- Repository name stays `frob` (the umbrella, like `ruff` hosting ty).
- License: everything MIT, including the frob binary (v1 was
  GPL-2.0-only). The repo `LICENSE`, README badge, and `Cargo.toml`
  `license = "MIT"` on every crate change in the first scaffolding
  ticket; the v1 branch keeps its GPL history untouched.
- Substrate prefix is `gob-` (as in glob). The crates.io name `gob`
  itself is taken (a 2018 serde codec), which does not matter: the
  prefixed names (`gob-rules`, `gob-symbols`) are free and are published
  with the rest of the crate set (section 4). See products.md section 5
  for name reservation.
