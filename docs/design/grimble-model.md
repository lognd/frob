# grimble: the system-design model and its code binding

Status: DRAFT (T-0001, a v1-format id that migrates with an alias). Ownership after products.md: this is the grimble model (v1 name: strata), crates `grimble-model`, `grimble-kernel`, `grimble-bind`. Inputs: notes/v1/strata.md (surface grammar,
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

## 2. Core grammar (kept, tightened)

```
module frob                              // root file; `part of frob` for fragments

node cli : trusted {
  clearance Internal;
  owns "crates/frob/**";                 // selector list (section 4)
  owns "crates/frob-check/src/lib.rs::run";
  may fs.read, fs.write at "crates/frob/**";
  may net.connect:api.github.com at "crates/frob-gh/src/lib.rs::GhClient.*";
  excuses net.listen reason "a CLI never serves";
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
defer SYS005 on cli ticket 01J9QKX3M8Z4T7N2V5B6C0D1E2 reason "producer lands next cycle";
```

Changes from v1 grammar:

- `owns` replaces `code`: real path globs (`**` crosses dirs, `*` does
  not), optional `::qualname-glob`, optional kind filter. Most specific
  selector wins; equal specificity on one symbol is an error; unclaimed
  symbols are FOREIGN.
- `may` scopes are selectors (`at`), and argument constraints (`of`)
  are resolved from the call AST, not the first string on the line.
- `excuses ATOM reason "..."` is the explicit matrix exclusion.
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
  RULE on NODE because "..."`, `defer ... ticket ID reason "..."` and
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
| `excuses ATOM reason` | node | matrix cell `excused` |
| `surface SELECTOR` | node | intended public symbols |
| `flow via producer/consumer/contract` | flow | three symbols, any languages |
| `vmodel ... ref / runnable` | vmodel | doc anchor or test symbol |
| `grimble:node N`, `grimble:channel F role=producer`, `grimble:boundary B`, `grimble:effect ATOM because "..."` | code comments (grimble namespace; frob never reads them) | attestations checked against the model |

Drift findings (all computed from the code graph and the model on every
check; each is one generated rule in `grimble-bind` or
`grimble-capabilities`). Ids are `FAMILYNNN` with a slug alias, the same
grammar as every other product (v1's 51 SYS ids collapse many-to-one
into these; rules.md section 3):

| Id | Alias | Condition |
|---|---|---|
| SYS001 | SYS-UNRESOLVED | selector matches zero symbols |
| SYS002 | SYS-AMBIGUOUS | symbol claimed by two equally specific selectors |
| SYS003 | SYS-UNMODELED | symbol with effects or public visibility claimed by no node; evaluated only for selectors listed in `[grimble] modeled` in `grimble.toml` (opt-in, not a repo-wide Warn) |
| CAP001 | CAP-EXCEEDS | observed capability at a symbol with no covering grant (the v1 SYS100); Error |
| CAP002 | CAP-STALE | grant never observed at its scope (shrink-only fix); Warn |
| CAP003 | CAP-UNEXCUSED | capability atom applicable to the node's languages, neither granted nor excused; Advisory for one release after a new atom or detector ships, then Warn |
| SYS004 | SYS-UNDECLARED-FLOW | import or call edge between two owners with no flow in that direction (v1 SYS003, now every language) |
| SYS005 | SYS-UNIMPLEMENTED-FLOW | flow declared, producer or consumer selector empty |
| SYS006 | SYS-CONTRACT-SKEW | contract symbol fingerprint differs between the producer and consumer acks recorded with `grimble ack` in `grimble.lock` |
| SYS007 | SYS-CHANGED | bound symbol's body digest changed since the last `grimble ack` in `grimble.lock` (the same mechanics as `frob.lock` from `gob-lock`, a separate file) |
| SYS008 | SYS-RENAMED | bound symbol vanished, same-digest symbol appeared elsewhere (suggest, never edit) |
| SYS009 | SYS-SURFACE | public symbol outside `surface` |

grimble has its own `ack` verb and `grimble.lock`; it never reads
`frob.lock`, and frob never reads `grimble.lock`.

Capability observation moves from substring needles to typed call-site
detectors (IR patterns plus resolved callee), held in a data registry
with v1's row schema (language, library, pattern, capability, cwe,
rationale, safer alternative, severity). A language without a detector
for an atom reports that cell as `n/a`, and the summary carries one
Unresolved per node (not per cell) so an unmeasured node never reads as
clean.

Cross-language flows: FFI, IPC, and HTTP edges are never inferred from
text. They are declared flows with a contract symbol; the check is
"producer exists, consumer exists, contract fingerprint acknowledged on
both sides". Where a `binds` edge exists (code-model.md section 6) the call graph
crosses it, so a Python handler calling a Rust kernel through PyO3 is
one resolved edge and an undeclared flow is caught.

## 5. Data packs

Threat obligations (capability -> obligation discharged by a claim at a
rung), reliability markers (one "marker plus evidence" rule shape, not
51 REL ids), compliance views, CVE fingerprints, and PII categories ship
as TOML packs under `packs/` and are enabled per repo in `grimble.toml`
(`[grimble] packs = ["threat", "reliability"]`). Milestone 2 or later
(D36). A pack contributes
capability atoms, detectors, obligations, and rule parameters; it never
contributes grammar.

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
- Exceptions that name a ticket (`defer`, `hotfix`): grimble parses the
  `ticket=` value as opaque and emits it in `--json`; standalone grimble
  reports such an exception as Unresolved-exit, and frob evaluates the
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
B subset of E x I x {Must, May, Unknown} produced by four sources in
this precedence: explicit `grimble:binds` directives in code (Must);
`owns` selectors in the model resolved through gob-walk and the
scope graph (Must for literal paths, May for globs that match units
with Unknown edges); inference from names and attributes declared by
data packs (May); and nothing (Unknown, reported as SYS-UNRESOLVED,
never as clean). The twelve v1 mechanisms map onto these four sources
in notes/review/grimble-review.md section 2; none survives as its own
mechanism. "Human symref canonical, SCIP derived" stands: the symref is
the human-facing name of an identity, SCIP occurrences are one more
inference source at May.

### 9.2 Identity, rename and the lock

An identity is the stable symref-anchored id of a `unit`; its content
hash is a facet, not the identity. SYS008 (renamed) is detected as a
new identity whose body facet equals a disappeared identity's body
facet; SYS007 (changed) is the same identity with a different facet.
Lock entries (gob-lock) are typed: key = identity, fields = the facet
digests, the role (producer, consumer, plain) and the flow key where
the entry backs a contract, so SYS-CONTRACT-SKEW compares the two ends
of one flow. The lock file carries a `digest_scheme` version separate
from the file format version; a scheme change invalidates acks loudly
(every entry becomes REATTEST) instead of silently. Digests are
computed over the canonical facet stream of U (universal-model.md 7,
items G7-G9), not over collapsed text.

### 9.3 .grmb is a language with an adapter

grimble-model owns a U adapter for .grmb at fidelity F4: entities are
`unit` nodes (kinds node, flow, contract, claim, vmodel, pack), selector
expressions are `apply(kind=select)` with May edges to the units they
match, `excuses` and the four exception kinds are `attr` nodes, and
directives (`frob:doc`, `frob:ticket`, `grimble:...`) bind to entities
exactly as they bind to code units. Consequently every frob rule that
works on code works on the model (DRIFT between a design doc and its
.grmb entity, REF from an entity to a ticket), and `grimble fmt` is the
alpha-normal printer. The grammar specification (lexical rules,
scoping of entity names, includes across files, versioning) is ticket
G01; until it lands, the examples in sections 1-3 are illustrative.

### 9.4 Drift on partial languages

SYS-CHANGED, SYS-CONTRACT-SKEW and CAP-STALE are equality rules
(polarity P0 in universal-model.md 4.2). On an F0 or F1 language, or on
an identity whose facets touch `opaque`, they report Unresolved with
the fidelity reason, never clean and never changed. A standalone
grimble run computes digests itself through gob-symbols and gob-lock;
frob never does it on grimble's behalf (D28).

### 9.5 The sibling contract and absence

`grimble check --json` emits a versioned document (schema in
docs/schemas/sibling.json, generated): schema_version, product,
fidelity per language, findings with rule id, severity including
Unresolved with reason codes, polarity, subject count, exception (kind,
reason, opaque `ticket=`), suppressed findings, and the entity and
binding lists frob may display. frob validates the schema version and
refuses on mismatch. When grimble.toml exists and the binary is absent
or incompatible, `frob check` emits one Unresolved finding per missing
product AND fails the gate by default (`[check] require_siblings =
true`, materialized), closing the audit's "absent grimble passes" hole;
Severity ordering is amended so that Unresolved can fail when a rule
declares it must (subject accounting, universal-model.md 4.2).

### 9.6 The capability matrix, one definition

Cells are: uses (detector fired, Exact), undeclared (uses without a
grant: CAP001), declared-unused (grant without a use: CAP002),
excused (grant waived with reason), and unknown (no detector for this
atom in this language, or the detector answered Unknown). `n/a` is
retired; `unknown` is reported as Unresolved in the summary, one per
node, never as clean. Each atom is registered with its detector kind
per language (query over U, callee vocabulary, attribute, pack-declared
pattern, or none); data packs may add atoms and detectors because the
atom registry lives in a shared `gob-*` crate as inventory entries, not
as a closed Rust enum. A language with no detectors yields a column of
`unknown` and one summary Unresolved per node.

### 9.7 Orchestration and crates

The check pipeline (walk, inputs, per-file and repo rules, exceptions,
render) moves from frob-check into a substrate crate `gob-check` that
both frob and grimble drive; exception matching moves into gob-rules.
grimble depends on gob-walk, gob-cache, gob-exec, gob-ir, gob-symbols,
gob-lock, gob-check and gob-rules, never on a frob crate. The verbs are
check, status, graph, shrink, init, doctor, fmt, packs, explore, ack,
exceptions, migrate and serve --mcp; owners per boundaries.md are fixed
in the review's section 8 and the milestone-2 cut (19 tickets, critical
path T-IR, G01, G02, G07, G08, G09, G11, G14, about 70 points; first
visible value is model-free CYCLE after the binary skeleton).

### 9.8 What grimble needs from U that U must add

A stable identity separate from the content hash (done above, to be
written into universal-model.md 2.2); selector semantics as a U query;
detector and atom registries in shared crates; `norm_sig` in the adapter
contract; a build-manifest reader (Cargo.toml, pyproject, package.json)
as an F2 adapter so ownership can follow packages; polarity and subject
count on Rule and Finding types.
