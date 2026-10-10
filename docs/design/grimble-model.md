# grimble: the system-design model and its code binding

Status: draft
Owner: grimble
Decisions: D36
Audience: contributor

Provenance: written under T-0001 (a v1-format id that migrates with an alias). Ownership after products.md: this is the grimble model (v1 name: strata), crates `grimble-model`, `grimble-kernel`, `grimble-bind`. Inputs: notes/v1/strata.md (surface grammar,
kernel, 12 binding mechanisms, rule inputs, measured adoption), the
binding requirement in goals.md, code-model.md.

Milestone 2 or later (D36): this whole file.

## 1. What the grimble model is, in one sentence

A typed architecture graph (nodes, flows, boundaries, claims, and a
V-model of requirements, designs, tests) whose elements bind to code
SYMBOLS in any language, checked by a small semantic kernel, with every
optional vocabulary (threat catalogs, reliability markers, compliance,
hosts) loaded as data packs rather than grammar.

Measured v1 adoption drives the cut: every consumer uses node, flow,
code, may, assert/assume, waive (now the exception kinds); two use the V-model; zero use policy,
scenario, refine, entity/architecture/configuration, host, Kerberos,
deploy, or the six-phase boundary grammar. 79 of 139 v1 keywords never
reached the prover.

The planning layer (grmb-planning.md, D124-D133) adds the left arm of
the V above the architecture: actors, goal variant trees, scenarios of
steps with typed outcomes and exhaustive handling, and impl blocks that
bind steps to code; it is the one behaviour construct, kept because it
is checkable.

## 2. Core grammar (kept, tightened)

```
module frob                              // root file; `part of frob` for fragments

node cli : trusted {
  clearance Internal;
  owns "crates/frob/**";                 // selector list (section 4)
  owns "crates/frob-check/src/lib.rs::run";
  may fs.read, fs.write at "crates/frob/**";
  may net.connect:api.github.com at "crates/frob-gh/src/lib.rs::GhClient.*";
  surface pub fn *, "Cli";                // intended public API, subset-checked
  attr timeout = 30 s;                    // typed attrs: number+unit | ident | string
}

store ledger : trusted { engine git_tracked; append_only; owns "tickets/**"; }

flow f_parse : cli -> symbols {
  label Internal; rate 100 req/s;
  via producer "crates/frob-check/src/lib.rs::run"
      consumer "crates/gob-symbols/src/lib.rs::parse_file"
      contract "crates/gob-symbols/src/lib.rs::ParsedFile";
}

boundary b_vet endorse f_install : foreign -> trusted when "checksum_verified";

assert noflow registry -> vet;
assume "weakness:CWE-78:vet" noflow registry -> vet owner logan review 2026-10-15;

vmodel req_1 kind artifact level requirements ref "docs/req.md#REQ-1";
vmodel t_1  kind test level unit runnable "crates/x/tests/t.rs::parses";
vmodel t_1 verifies req_1;

accept SYS004 on cli because "docs/decisions/2026-10-02-bootstrap-path.md";
defer SYS005 on cli ticket 01J9QKX3M8Z4T7N2V5B6C0D1E2 because "producer lands next cycle";
```

Changes from v1 grammar:

- `owns` replaces `code`: real path globs (`**` crosses dirs, `*` does
  not), optional `::qualname-glob`, optional kind filter. Most specific
  selector wins; equal specificity on one symbol is an error; unclaimed
  symbols are FOREIGN.
- `may` scopes are selectors (`at`), and argument constraints (`of`)
  are resolved from the call AST, not the first string on the line.
- Capabilities are denied by default (D75): a node has `may` grants and nothing else; an ungranted atom is denied and its observed use is CAP001. The v1-era node clause `excuses ATOM because "..."` is removed (MDL018); excuses exist only in matrix-build templates (grmb-spec 4.7, packs.md 6.7).
- `surface` replaces `attr interface=[...]` lists.
- `flow ... via producer/consumer/contract` gives flows symbol-level
  endpoints; cross-language flows need no special syntax.
- Typed attrs (number with unit, ident, string, list) so markers carry
  magnitude. Units are types as in v1.
- Every construct has a stable id and the parser emits spans for all of
  them (v1 regex-located spans are gone).
- Multi-file from day one: `part of` fragments can declare anything,
  not only `extend node`.
- `waive` is replaced by the exception kinds of exceptions.md: `accept
  RULE on NODE because "..."`, `defer ... ticket ID because "..."` and
  `hotfix ...`; `baseline` pools stay in `grimble-ratchet.lock.json`.
  The `ticket` value is opaque to grimble.

Dropped from grammar (available as data packs or not at all): host,
krb, deploy, cdn/balancer/queue/cache/secret/resource as keywords (they
become `node ... kind queue` with typed attrs), operation/saga/crash/
breach, six-phase boundary blocks, policy Tier-2, scenario, refine,
entity/architecture/configuration, carries (PII becomes a capability
pack), import/export/layer.

## 3. Kernel

Crate `grimble-kernel`, ported from the v1 strata kernel (Rust already): label closure over flows with
boundary endorse/declassify, SCC longest-path age, summed demand and
capacity utilisation, V-model closure (paired levels, five structural
rules, milestone known gaps), claim verdicts PROVED / REFUTED(witness) /
UNPROVABLE with auto-generated assumes, assume ownership and expiry.
Everything else is a join between the model and the code graph.

## 4. Binding (the point of the exercise)

Model side declares intent and ceilings; code side carries sparse
attestations; neither side is ever auto-regenerated to match the other
(the v1 "never auto-widen" lesson). Shrink-only automation is allowed
(`grimble shrink` removes grants never observed, with a reason).

| Declared | Where | Resolves to |
|---|---|---|
| `owns SELECTOR` | node, store | set of symbols (code-model.md section 2 addresses) |
| `may ATOM at SELECTOR of CONSTRAINT` | node | capability grant scoped to symbols |
| `excuse ATOM for SELECTOR because` | matrix-build template (pack or `template` entity), never a node | matrix cell `excused`; a use in covered code is CAP004 |
| `surface SELECTOR` | node | intended public symbols |
| `flow via producer/consumer/contract` | flow | three symbols, any languages |
| `vmodel ... ref / runnable` | vmodel | doc anchor or test symbol |
| `grimble:binds SYMREF via="manual"`, `grimble:node N`, `grimble:channel F role=producer`, `grimble:boundary B`, `grimble:effect ATOM because "..."` | code comments (grimble namespace; frob never reads them) | attestations checked against the model; `grimble:binds` is the highest-precedence binding source (9.1). Effect claims about a unit (`frob:effects`) are a different directive in the `frob:` namespace, evaluated by NEAT (code-model.md section 4) |

Drift findings (all computed from the code graph and the model on every
check; each is one generated rule in `grimble-bind` or
`grimble-capabilities`). Ids are `FAMILYNNN` with a slug alias, the same
grammar as every other product (v1's 51 SYS ids collapse many-to-one
into these; rules.md section 3):

| Id | Alias | Polarity | Condition |
|---|---|---|---|
| SYS001 | SYS-EMPTY-SELECTOR | P- | selector matches zero symbols (fires iff `hi` is empty) |
| SYS002 | SYS-AMBIGUOUS | P+ | symbol claimed by two equally specific selectors |
| SYS003 | SYS-UNMODELED | P+ | symbol with effects or public visibility claimed by no node; evaluated only for selectors listed in `[grimble] modeled` in `grimble.toml` (opt-in, not a repo-wide Warn) |
| CAP001 | CAP-EXCEEDS | P+ | observed capability at a symbol with no covering grant (the v1 SYS100); Error |
| CAP002 | CAP-STALE | P- | grant never observed at its scope (fires iff `hi` lacks a use; shrink-only fix, tied to Exact absence); Warn |
| CAP003 | CAP-UNEXCUSED | retired | RETIRED by D75 (the id is never reused). It reported a blank matrix cell as missing model completeness; under deny-by-default a blank cell means "denied", which is a decision and not a gap, so there is nothing to report until a use is observed (CAP001) |
| CAP004 | CAP-EXCUSED-USED | P+ | code covered by a matrix-build template excuse is observed using the excused atom (an excuse never masks an observed use; binding.md 7.2); Error. Uncertain detection (May or Unknown use, missing detector, F0 or F1 fidelity) is Unresolved, never a pass |
| SYS004 | SYS-UNDECLARED-FLOW | P+ | import or call edge between two owners with no flow in that direction (v1 SYS003, now every language) |
| SYS005 | SYS-UNIMPLEMENTED-FLOW | P- | flow declared, producer or consumer selector empty |
| SYS006 | SYS-CONTRACT-SKEW | P0 | the `contract` facet digests (code-model.md section 2) of the contract symbol differ between the producer and consumer acks recorded with `grimble ack` in `grimble.lock` |
| SYS007 | SYS-CHANGED | P0 | bound symbol's body digest changed since the last `grimble ack` in `grimble.lock` (the same mechanics as `frob.lock` from `gob-lock`, a separate file) |
| SYS008 | SYS-RENAMED | P0 | bound symbol vanished, same-digest symbol appeared elsewhere (suggest, never edit) |
| SYS009 | SYS-SURFACE | P+ | public symbol outside `surface` |

The ids, polarities and conditions of this table are superseded by
binding.md section 6 (SYS001-SYS012; its 11.3 maps the old ids to the
new ones). CAP001 and CAP002 are unchanged, CAP003 is retired and CAP004 is added (D75); SYS012 is redefined as a matrix-build check (binding.md 6.12).

grimble has its own `ack` verb and `grimble.lock`; it never reads
`frob.lock`, and frob never reads `grimble.lock`.

Capability observation moves from substring needles to typed call-site
detectors (queries over U plus resolved callee), held in the detector
registry of 9.6 (row schema there). A language without a detector for
an atom reports that cell as `unknown` (or `not-applicable` when the
detector declares the capability impossible there), and the summary
carries one Unresolved per node for the unknown cells (not per cell)
so an unmeasured node never reads as clean.

Cross-language flows: FFI, IPC, and HTTP edges are never inferred from
text. They are declared flows with a contract symbol; the check is
"producer exists, consumer exists, contract fingerprint acknowledged on
both sides". Where a `binds` edge exists (code-model.md section 6) the call graph
crosses it, so a Python handler calling a Rust kernel through PyO3 is
one resolved edge and an undeclared flow is caught.

## 5. Data packs

Threat obligations, reliability markers, compliance views, CVE
fingerprints, PII categories and every other optional vocabulary ship as
data packs, never as grammar; milestone 2 or later (D36). A pack
contributes capability atoms, detectors, callee vocabularies, inference
rules, claim templates, node kinds and (decision pending) lattice
extensions. packs.md (G04) is the definition: the pack format and its
JSON Schema, where packs live (built-in as inventory entries of the
shared registry crate, repository `packs/`, external by URL and digest),
the drift-lock `grimble.packs.lock`, materialization, how detectors
become matrix cells, and the three built-in packs `core-effects`,
`ci-github` and `rust-ecosystem`. This file does not repeat it.

## 6. Registry drift-lock

Kept in spirit: a registry row names a concept and its disposition
(`handled_by RULE`, `deferred ticket=<ulid>` with the ticket opaque to
grimble, `duplicate_of`, `out_of_scope caught_by`). In v2 the registry is generated from rule metadata plus
pack data, and the only hand-written part is dispositions for concepts
with no rule yet. Rows whose deferred ticket closes go red, as in v1.

## 7. What frob gets from this (grimble never knows about tickets)

- Tickets link to grimble entities with an `implements` link
  (`design:node/cli`); frob validates the target only through
  `grimble graph --json` (Unresolved when grimble is absent). An epic can
  be "implement flow f_parse", and the flow's SYS005 finding closes when
  the ticket lands.
- Planning entities (`goal/...`, `scenario/...`, `impl/...`) are
  `implements` targets too; grimble emits their `status` and
  `obligations` in the graph export and frob adds the close guard
  `design_bound`, PM037-PM039 and `frob plan --from-design`
  (grmb-planning.md 9 and 10).
- Exceptions that name a ticket (`defer`, `hotfix`): grimble parses the
  `ticket=` value as opaque and emits it in `--json`; standalone grimble
  reports such an exception as UnresolvedExit, and frob evaluates the
  exit and the close guard from that JSON (exceptions.md section 2).
- The V-model is the requirements-to-tests traceability Jira lacks:
  requirement -> design decision -> ticket -> test, all symbols, all
  checked.
- `grimble status` renders the model with per-node drift counts;
  `grimble graph --dot|--json` exports it; the frob GUI (gui.md) shows
  the same through grimble's `--json`.

## 8. Open questions

Decided 2026-10-02: `.grmb` is its own language with its own parser
(leaf crate, spans for every construct, JSON export on day one, editor
grammar generated from the keyword table); FOREIGN symbols are Warn
until `[grimble] strict = true` in `grimble.toml`.

## 9. Revision after the universal model (2026-10-04, DRAFT for review)

notes/review/grimble-review.md audited this file against
universal-model.md and found 4 HIGH, 12 MEDIUM and 7 LOW gaps. The
decisions below resolve the HIGH ones and set the frame for the
milestone-2 design tickets G01-G04 (full .grmb specification, binding
semantics, sibling JSON contract, packs and drift-lock), which must land
before any grimble crate is built.

### 9.1 What "binds" is

A model is a set of entities E (nodes, flows, contracts, claims,
V-model links) declared in .grmb files. The code is a U term with
identities I (universal-model.md 2.2). Binding is a relation
B subset of E x I x {Must, May, Unknown}, produced by four ranked
sources: explicit `grimble:binds` directives (Must), model selectors
resolved through gob-walk and the scope graph (Must or May), pack
inference (May) and nothing (Unknown). binding.md (G02) is the
definition: the relation with roles and provenance, the precise
semantics and precedence of the four sources, the merge and conflict
rules, how SCIP and LSP occurrences enter, what each of the twelve v1
mechanisms became, identity and rename over commits, and the rules
SYS001-SYS012 as predicates over B with their polarity and Unresolved
conditions. "Human symref canonical, SCIP derived" stands: the symref
is the human-facing name of an identity and SCIP occurrences are one
more inference source at May (binding.md section 3).

### 9.2 Identity, rename and the lock

An identity is the stable symref-anchored id of a `unit`; its content
hash is a facet, not the identity. SYS008 (renamed) is detected as a
new identity whose body facet equals a disappeared identity's body
facet; SYS007 (changed) is the same identity with a different facet.
Lock entries (gob-lock) are typed. gob-lock gains `kind = symbol |
flow`, `digest_scheme` and an optional `attr` facet; `frob.lock` uses
`symbol` entries only and `grimble.lock` uses both; the ack planner
moves from frob-ack to gob-lock (ticket G05); `LOCK_VERSION` is bumped
with a reader for version 1 (code-model.md section 2 has the lock
mechanics). A `flow` entry is keyed by the flow and carries the role
(producer, consumer, contract) and the `contract` facet digest of its
end, so SYS-CONTRACT-SKEW compares the two ends of one flow over the
language-neutral Contract facet, not over per-language `sig` digests
(a TS producer and a Rust consumer have different sig digests by
construction). The lock file carries a `digest_scheme` version separate
from the file format version; a scheme change makes every entry stale
(DRIFT, re-ack required) and says why, instead of silently rewriting
digests (REATTEST is an exception state of `accept`, not the drift
state). Digests are computed over the canonical facet stream of U
(universal-model.md 7.1; facets Sig, Body, Doc, Attr and Contract), not
over collapsed text.

### 9.3 .grmb is a language with an adapter

grimble-model owns a U adapter for .grmb at fidelity F4: entities are
`unit` nodes (kinds node, flow, contract, claim, vmodel, pack, template), selector
expressions are `apply(kind=select)` with May edges to the units they
match, and the four exception kinds are `attr` nodes (a matrix-build `template` is a unit of kind template whose `excuse` clauses are `attr` nodes), and
directives (`frob:doc`, `frob:ticket`, `grimble:...`) bind to entities
exactly as they bind to code units, so inside grimble every rule that
works on code works on the model, and `grimble fmt` is the alpha-normal
printer. frob cannot link grimble-model (products never depend on each
other, D28), and the substrate `Language` registry cannot name a
product adapter; so frob binds a `frob:` directive in a .grmb file only
from `grimble graph --json` (schema `grimble.graph/1`, generated at
docs/schemas/ next to sibling.json): the entity list with spans and
Body and Doc facet digests, from which DRIFT between a design doc and
its entity and REF from an entity to a ticket are evaluated. A frob
without grimble sees .grmb as F0 opaque, and a `frob:` directive inside
it is reported Unresolved, never silently unbound. The grammar
specification (lexical rules, scoping of entity names, includes across
files, versioning) is ticket G01; until it lands, the examples in
sections 1-3 are illustrative. Which files form a model is decided by
declared roots (`[grimble] models`), not by the walk: only files reachable
from a root through `include` load, an unreachable file is the orphan
warning MDL019, and an include may not climb above its own directory
without the `outside` marker (grmb-spec.md section 3, D77).

### 9.4 Drift on partial languages

SYS-CHANGED, SYS-CONTRACT-SKEW and SYS-RENAMED are equality rules
(polarity P0 in universal-model.md 4.2); CAP-STALE is P- (it fires
only when `hi` lacks a use, so `grimble shrink` acts only on Exact
absence). On an F0 or F1 language, or on an identity whose facets touch
`opaque`, the P0 rules report Unresolved with the fidelity reason, never
clean and never changed. A standalone grimble run computes digests
itself through gob-symbols and gob-lock; frob never does it on
grimble's behalf (D28).

### 9.5 The sibling contract and absence

`grimble check --json` emits a versioned document, `gob.sibling/1` (schema in
docs/schemas/sibling.json, hand-written until the derive generates it)
whose fields, version negotiation, merge rules and failure cases are
defined once in sibling-contract.md; the `grimble.graph/1` export of 9.3
is section 3.8 there. frob validates the schema version and the compute
digest. When grimble.toml exists and the binary is absent
or incompatible, `frob check` emits one Unresolved finding per missing
product marked `required`, so the gate fails with exit 1 under the
default `[check] fail_on_unresolved = "required"` and `[check]
require_siblings = true` (both materialized); cli.md section 2 is the
one definition of this mechanism and it closes the audit's "absent
grimble passes" hole. A standalone grimble run applies the same
mechanism to its own required Unresolved findings.

### 9.6 The capability matrix, one definition

Capabilities are denied by default (D75): a regular node's atom that is
not granted is denied, a blank cell means "denied" and not "not yet
considered", and an observed use without a grant is CAP001. Cells are:
uses (detector fired, Exact), undeclared (uses without a grant: CAP001),
declared-unused (a grant without a use: CAP002), denied (blank: no grant
and no use; no finding), excused (a matrix-build template excuse covers
the unit; shown as excused only when no use is observed, a use in
excused code is shown as uses and raises CAP004), not-applicable (the
atom's detector for this language declares the capability impossible,
for example CSS has no network) and unknown (no detector for this atom
in this language, or the detector answered Unknown). `n/a` is retired
as a spelling. `not-applicable` is reported in the matrix and is never
Unresolved; `unknown` is reported as Unresolved in the summary, one per
node, never as clean. A language with no detectors yields a column of
`unknown` and one summary Unresolved per node.

The atom registry lives in `gob-ir` as inventory entries, not a closed
Rust enum, so data packs add atoms and detectors with a pack-qualified
id. Atoms are hierarchical (`fs` covers `fs.read` and `fs.write`).
There is one callee-vocabulary table per language; the NEAT
`[neat.effects]` tables and grimble's detectors are views over it, and
both `frob:effects` claims and `grimble:effect` attestations name atoms
from the one registry (adding `tokio::fs` once serves both). The
detector registry row is `{atom, language, detector_kind,
pattern_or_vocab_ref, precision: Typed | Lexical, cwe, rationale,
safer_alternative, severity}` with `detector_kind` one of query over U,
callee vocabulary, attribute, pack-declared pattern, or none; it is
exposed as the U capability query `detectors(lang, atom) ->
NotApplicable | None | Some(precision)`.

### 9.7 Orchestration and crates

The check pipeline (walk, inputs, per-file and repo rules, exceptions,
render) moves from frob-check into the substrate crate `gob-check`
that both frob and grimble drive; exception matching moves into
gob-rules (today it lives in frob-obligations' `apply_exceptions`;
ticket G06 moves it). grimble depends on gob-walk, gob-cache, gob-exec,
gob-ir, gob-symbols, gob-lock, gob-check and gob-rules, never on a frob
crate. The verbs are check, status, graph, shrink, init, doctor, fmt,
packs, explore, ack, exceptions, migrate and serve --mcp; `vet`
follows the cut (cli.md section 4). The milestone-2 order, the 19
tickets G01-G19 and the critical path are stated once in
build-test-ci.md, Milestone 2; this file does not repeat them. Crate
owners per boundaries.md, including grimble-lints (NEAT) and the new
grimble-ci crate (CI, DK).

### 9.8 What grimble needs from U that U must add

A stable identity separate from the content hash (done in
universal-model.md 2.2); selector semantics as a U query; detector and
atom registries in shared crates (9.6); the `contract` facet in the
adapter contract (universal-model.md 7.1; replaces the earlier
normalized-signature query); a build-manifest reader (Cargo.toml,
pyproject, package.json, and the repository's CI files for CI012) as an
F2 manifest adapter so ownership can follow packages and CI can be
joined to the repository; polarity and subject count on Rule and
Finding types (rules.md section 2).
