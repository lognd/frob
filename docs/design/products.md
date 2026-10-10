# Product split: three goblins, one workspace

Status: current
Owner: gob
Decisions: none
Audience: contributor

Provenance: written under T-0001 (a v1-format id that migrates with an alias). Owner direction 2026-10-01: make the
responsibilities of frob and crunk unmistakable; rename strata (v1 name) into its
own goblin-named tool; decide whether the structural linter and the
design model belong together.

## 1. The split

| Product | One-line job | Owns | Never does |
|---|---|---|---|
| frob (ticket goblin) | accounts for WORK: tickets, scope leases, worktrees, evidence, landing, releases, the obligation gates that tie code to tickets, docs, and tests | tickets/, frob.lock acks, frob-ratchet, invariants/, decisions/, land, release, fleet, MCP for agents | parse CSS semantics, judge architecture, lint code style |
| grimble (the design goblin) | judges STRUCTURE: the architecture model (what v1 called strata), symbol binding, capability matrix, universal and language-specific structural lints, neatness (NEAT), CI and Dockerfile policy (CI, DK), cycles, dup, dead code, arch metrics, security patterns | design/*.grmb, `grimble.lock`, packs/, rule packs for code structure | know what a ticket is (it parses `ticket=` in an exception as an opaque string), land anything |
| crunk (front-end design-system goblin) | judges front-end DESIGN TOKENS: palette, scales, organization, Tailwind, contrast, token export, gallery; and, as a rule pack (D88/D89), front-end web lint (accessibility, SEO, launch readiness, markup and asset performance) | crunk.toml, tokens, CSS/TSX ingest, gallery | know what a ticket is (same opaque `ticket=` rule), model architecture |

The line between frob and the design goblin: frob asks "is this change
accounted for?" (ticket, doc, test, ack, scope); the design goblin asks
"is this code shaped the way the design says?" (binding, flows,
capabilities, cycles, patterns). frob consumes the design goblin's
findings as one more gate family and lets tickets link to its
entities, in both cases only through `grimble --json`; the design goblin
has no idea tickets exist.

The line between the design goblin and crunk: the design goblin models
systems and code structure in any language; crunk models a visual
design system and front-end files. crunk's TS/CSS parsing comes from
`gob-*` crates, but its rules are about colors, scales, and buckets,
not architecture. They never overlap because crunk rules take a
DesignSpec as input and design-goblin rules take an architecture model
and a code graph.

## 2. Do the structural linter and the design model belong together?

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

## 3. Naming (decided 2026-10-01)

The design goblin is **grimble** (owner: reminiscent of "grumble", what
you do when you realize you started with a bad design). Binary
`grimble`, crates `crates/grimble-*`, model files `design/*.grmb`, the
model language is called grimble too; "strata" survives only as the v1
name in notes/ and the migration map. Availability checked 2026-10-01:
free on crates.io and PyPI. Alternatives considered: gnarl (PyPI taken),
snag and skulk (both taken), krenk (free, too close to crunk).

## 4. What moves where (relative to the earlier files)

| Earlier location | Now |
|---|---|
| code-model.md sections 5 (IR), 6 (binds), 7 (capabilities) | grimble (`grimble-lints`, `grimble-bind`, `grimble-capabilities`), with `gob-ir` (the universal model, D56) and `gob-symbols` (its adapters) providing U terms and symbols to all three |
| rules.md families CYCLE ARCH LARGE DEAD DUP SEC PII SYS CAP BIND GPOL | grimble |
| rules.md families DRIFT AFFECT COV TODO SCOPE PRE QUEUE INV TEST TDD DOC DOCENUM NEGEXIST REF TICK MILE DEPR REL VERSION REG DEC NARR POL PM, and the ticket-bound exits of EXC | frob (the authoritative table is boundaries.md section 2.5) |
| grimble-model.md | grimble's model |
| `frob check` | runs frob's gates and, when grimble or crunk is installed, runs their checks in-process (feature `bundle`) or via their `--json` and merges findings into one report through the shared `gob-rules` registry |
| v1 `vet` | grimble (`grimble-vet`): the capability model applied to dependencies |
| v1 `explore` verbs | both frob and grimble, as views over `gob-symbols` |

The shared registry means a waiver syntax, a severity model, a ratchet
pool, and a renderer serve all three products; `frob check` is the one
command an agent runs, and it reports `grimble` and `crunk` findings under
their own family prefixes.

The full capability-to-crate map, the placement test, and the splits
considered are in boundaries.md.

## 5. Name reservation (checked 2026-10-02)

| Name | crates.io | PyPI | Action |
|---|---|---|---|
| frob | taken by an unrelated 2022 crate (`panicbit/frob`, 0.1.2) | ours already | decided 2026-10-02: the Rust crate publishes as `frob-cli` (binary name stays `frob`, like `ruff_cli`); PyPI `frob` keeps shipping the wheel that bundles the binary; a transfer request for `frob` may be sent in parallel |
| grimble | reserved 2026-10-02 | reserved 2026-10-02 | done |
| crunk | reserved 2026-10-02 | ours already | done |
| gob-* | `gob` itself is taken; `gob-rules`, `gob-macros` reserved 2026-10-02; `gob-symbols`, `gob-ir` reserved at first publish | prefixed names free | crates.io receives the full crate set at release in lockstep versions (monorepo.md section 4, D35); names are reserved at first publish |
| frob-cli | reserved 2026-10-02 | not needed | done |

How to reserve: publish a minimal placeholder crate (version 0.0.0,
a README stating the intent, `description` and `repository` set) with
`cargo publish` after `cargo login` with a crates.io API token; crates.io
discourages squatting but accepts placeholders with a real project
behind them. On PyPI, upload a 0.0.0 sdist with `uv publish` (token
from the PyPI account) for `grimble`; PyPI has no reservation API.
Also create the GitHub repository names if separate repos are ever
wanted, and the `grimble` name on docs sites is automatic. The owner
holds the tokens, so this is a `! cargo login` / `! uv publish` step in
the terminal, not something the agent does.

## 6. Install story

Three binaries from one workspace, released independently
(`frob-v*`, `grimble-v*`, `crunk-v*`). D87 (owner decision 2026-10-03):
**one binary per package, composed by dependencies.**

| Channel | frob | grimble | crunk |
|---|---|---|---|
| PyPI (prebuilt wheels, five platforms) | `frob`: the `frob` binary only; depends on `grimble` and `crunk` pinned to the same version, so `pip install frob` / `uv tool install frob` installs all three | `grimble`: the `grimble` binary only, installable alone | `crunk`: the `crunk` binary only, installable alone (the Python crunk in lognd/crunk keeps publishing until the Rust crunk ships from this repository; both repositories are trusted publishers meanwhile) |
| crates.io (source) | `frob-cli` (binary `frob`) and its library crates | `grimble` and its library crates | `crunk` and its library crates, once they exist |
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
sibling's crates in-process when built with the `bundle` feature; a
build without it (crates.io `frob-cli`) that cannot find a configured
sibling reports it as a required Unresolved finding rather than
omitting it, and treats a sibling whose `--json` has another
`schema_version` the same way (exit 1 under the default
`[check] fail_on_unresolved = "required"`, cli.md section 2;
boundaries.md section 6).

## 7. One product front end (D97)

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
