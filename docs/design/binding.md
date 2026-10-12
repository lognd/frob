# Binding semantics over U (G02)

Status: draft
Owner: grimble
Decisions: none
Audience: contributor

Provenance: DRAFT under T-0001 (a v1-format id that migrates with an alias);
written under ticket 01M3Z712KRPYF3DQG6ZFCWVPS7 (G02). It makes
grimble-model.md section 9.1 precise: what "binds" means, which of four
ranked sources produces each fact, how the sources merge, what each of
the twelve v1 binding mechanisms became, how bindings survive commits
and renames, and the drift and binding rules SYS001-SYS012 as predicates
over the relation with their polarity and their Unresolved conditions.
Where this file and grmb-spec.md sections 6.5 or 10 disagree, this file
wins; section 11.3 lists every disagreement and every id this file
renumbers.

Inputs: grmb-spec.md (entities E, the selector grammar and the
specificity order of 6.5, the relation B and its four ranks in section
10, MDL001-018, open questions 1-12), grimble-model.md sections 4 and 9
(drift findings, the four sources, identity and rename, partial
languages, the cell set), universal-model.md 2.2, 2.6, 3, 4 and 7.1
(identities, symrefs, fidelity, the answer lattice, polarity, Theorem 3,
the facet digests), code-model.md sections 2, 6 and 7 (symref grammar,
cross-language `binds`, capability binding), notes/v1/strata.md section
4 (the twelve v1 mechanisms), notes/review/grimble-review.md (H1, M5,
M12, L2) and notes/research/lint-requirements.md (R28-R30, Q32, Q36,
Q42, the Prolog and notebook examples).

## 1. Definitions

### 1.1 The three sets

- E: the entities of one model (grmb-spec 10.1): the units of kind node,
  flow, contract, claim, vmodel, boundary and pack in the U term of the
  model's .grmb files. An entity has a full name; its identity is
  `(module, full name)` (grmb-spec 5.5).
- I: the identities of the code term (universal-model.md 2.2): every
  `unit` of every artifact in the walked snapshot, including the units of
  the model's own .grmb files and of documents. An identity is
  `(symref, unit kind)`: the symref (code-model.md section 2) is the
  human name and the anchor, the unit kind guards against a symbol that
  changes kind, and the facet digests are facets of the identity, not the
  identity (grimble-review H1 (b); universal-model.md 2.2). A multi-part
  unit (Prolog clauses of one predicate, partial classes) is ONE identity
  (universal-model.md 2.6).
- S = {Must, May, Unknown}, ordered Must > May > Unknown, the one status
  vocabulary of the design set (code-model.md section 6).

### 1.2 The relation B

grmb-spec 10.2 states `B subset of E x I x S`. This file refines it with
a ROLE, because an entity binds to code in several different ways and the
rules over B must not confuse them:

```
B  subset of  E x Role x I x S x Prov
Role = owns | producer | consumer | shape | runnable | ref | evidence
```

| Role | Entity kind | Clause or directive that contributes | Cardinality in I |
|---|---|---|---|
| owns | node | `owns SEL`; `grimble:binds design:node/N` | a function: each identity has at most one owner (2.6) |
| producer | flow | `producer SEL`; `grimble:binds design:flow/F role=producer` | a set |
| consumer | flow | `consumer SEL`; `... role=consumer` | a set |
| shape | contract | `shape SEL` | exactly one identity is required (SYS003 kind `ambiguous-singleton` otherwise) |
| runnable | vmodel (test) | `runnable SEL` | exactly one test unit is required |
| ref | vmodel (artifact) | `ref "SYMREF"` | exactly one unit (a code unit or a document anchor) |
| evidence | claim | `evidence tests SEL`, `evidence ref "SYMREF"`, `frob:tests` on a test (grmb-spec 8.3) | a set |

`may ... at SEL` and `surface SEL` bind capability scopes and the public
surface; they are evaluated with `sel` on demand (section 7 and SYS014 of
11.3), not stored in B, exactly as grmb-spec 10.2 says.

A ROW is `(e, role, i, s)`. For each `(e, role)` the relation yields an
`Answer<Set<Identity>>` of the universal-model.md 4.1 shape:

- `lo(e, role)`: the identities with a Must row.
- `hi(e, role)`: `lo` plus the identities with a May row plus one HIDDEN
  placeholder `hidden(r)` for every unseen remainder r (grmb-spec 6.4
  step 4: an artifact the selector matched that holds an `opaque`, an
  unexpanded `phase` or a `hole`, or an unreadable or oversized file; an
  F0 artifact under a symbol-level selector). A hidden placeholder is the
  Unknown row of grmb-spec 10.2, and it is never in `lo`.

"`hi` is empty" in this file always means: no Must row, no May row AND no
hidden placeholder. A selector that cannot see part of the code is
therefore never reported as matching nothing.

### 1.3 Facts and provenance

A FACT is a row with its provenance. Provenance is never optional and is
what makes every finding explainable:

```
Prov {
  source:   1 | 2 | 3 | 4              // the rank of section 2
  origin:   Directive { site, via }     // rank 1: where the directive sits, its via= value
          | Selector  { anchor, glob, specificity, path }
                                         // rank 2: clause anchor (node/cli/owns[1]),
                                         // which glob of a compound selector matched,
                                         // the specificity vector (grmb-spec 6.5), and the
                                         // chain of edges that gave the status
          | Inference { pack, pack_version, rule, evidence }
                                         // rank 3: the pack, the rule id, the names or
                                         // attributes that triggered it
          | Residual  { reason }         // rank 4: the unseen remainder and why
  adapter:  AdapterVersion             // adapter id and version of the artifact's language
  snapshot: Digest                     // the walk digest the row was computed against
}
```

B is DERIVED: recomputed on every check from the snapshot, the model and
the enabled packs; it is a pure function of them (determinism, 2.7). It is
never stored. What persists across commits is the lock (gob-lock) and the
model; section 5 says how rows are carried.

### 1.4 The companion relation C (identity to identity)

code-model.md section 6 defines the cross-language edge `binds(a, b,
via)`. It relates two code identities, not an entity and an identity, so
it is a second relation, called C here:

```
C  subset of  I x I x S x Via x Prov            Via = manual | pyo3 | pybind11 | ctypes | wasm-bindgen | jni | napi | ...
```

C is produced by the same four ranks (rank 1: `grimble:binds SYMREF
via="manual"` in code, rank 3: attribute and stub inference, `#[pyfunction]`,
`.pyi`; rank 4 is a missing counterpart, which BIND002 reports). B and C
share the merge rules of section 2; the BIND family itself (BIND001,
BIND002) is out of scope of this file. The graph query `binds(sym)`
(universal-model.md Q36) returns C, so that the call graph crosses a
binds edge (section 9.2).

### 1.5 Notation used by the rules of section 6

- `B(e, role)` is the Answer of 1.2; `lo(.)` and `hi(.)` read its bounds.
- `owner(i)` is the function of 2.6: `Answer<Option<Node>>`.
- `Facet(i, f)` is `Exact(digest) | Absent | Unknown` (Q38); `Contract(i)`
  is the Contract facet.
- `SG` is the scope graph; an edge has a status in S.
- `L(i)` is the language tag of i and `F(L)` its fidelity (universal-model.md
  3.3); `opaque-cone(i)` is true when the facets or edges a rule reads for i
  touch an `opaque` or `hole`.

## 2. The four ranked sources

Each fact has exactly one source. The sources are ranked; a lower number
is stronger.

| Rank | Source | Status it can give | Written by |
|---|---|---|---|
| 1 | explicit `grimble:binds` directive | Must (when its operand resolves uniquely) | a human, in code or in a .grmb file |
| 2 | model selector (`owns`, `producer`, `consumer`, `shape`, `runnable`, `evidence`) | Must or May, per grmb-spec 6.4 | a human, in a .grmb file |
| 3 | pack inference (and external index occurrences, section 3) | May | a data pack rule, requested by the model |
| 4 | nothing | Unknown | nobody: the residual of an unseen remainder, never a missing row |

### 2.1 Source (a): explicit directives

Syntax. The verb is `grimble:binds` (the namespace and the verb registry
are the shared ones of code-model.md section 4; grmb-spec 8.2 lists it).
Its operand has two forms, distinguished by a scheme prefix because a
bare path could be either:

```
// grimble:binds design:node/cli                 on a code unit: that unit is owned by node cli
// grimble:binds design:flow/f_walk role=producer  on a code unit: that unit is a producer of f_walk
# grimble:binds crates/scorer/src/lib.rs::py_score via="manual"   on a code unit: a C edge (1.4)
// grimble:binds crates/gob-walk/src/lib.rs::walk                  inside a .grmb entity: that entity binds that identity
```

1. Code side, entity operand `design:<kind>/<full name>` (the logical
   location of grmb-spec 5.5 and 9.1): the directive's TARGET unit (the
   unit the comment attaches to by the rule of code-model.md section 4)
   gets a Must row for the named entity. The role is `owns` for a node,
   the `role=` attribute for a flow (`producer` or `consumer`, required),
   `shape` for a contract, `runnable` or `ref` for a vmodel, `evidence`
   for a claim. `design:` is a new operand scheme (open question 11.2.6).
2. Code side, symref operand: a C edge from the target unit to the named
   identity (`via` defaults to `manual`).
3. Model side, symref operand inside a .grmb entity (grmb-spec 8.2): the
   entity gets a Must row for the resolved identity; for a flow it
   precedes a `producer`, `consumer` or `contract` clause and names the
   end by a `role=` attribute as in form 1.
4. The v1-derived spellings `grimble:node N`, `grimble:channel F
   role=R` and `grimble:boundary B` (grimble-model.md section 4) are
   sugar for form 1 and produce the same rank 1 row; they remain
   code-side only (MDL013 in a .grmb file, grmb-spec 8.2).
   `grimble:effect` attests a capability, not a binding, and belongs to
   grimble-capabilities (G14).

Resolution of the operand. A symref operand resolves by the symref
resolution order of code-model.md section 2 (exact, unique qualname,
unique suffix; query Q22). A unique resolution gives status Must. Two or
more candidates give May rows for each candidate and the finding SYS003
kind `ambiguous-operand` (the author wrote an ambiguous directive; it is
never silently narrowed). No resolution gives no row and SYS003 kind
`dangling-operand` (the v1 SYS001 "dangling is an error"). An entity
operand that names no entity of the model is `dangling-operand` too.

A rank 1 row is a statement by the author that is true by authorship, so
its status is Must independent of the fidelity of the language it sits
in, provided the operand resolved Must and the target unit is Must (a
directive that attaches to a unit through a May edge, for example inside
an unexpanded `phase`, gives a May row).

Conflicts inside rank 1 (the ticket's "MDL/SYS error"; it is SYS003, not
an MDL rule, because it needs the code snapshot to know two operands name
one identity):

- Two directives bind one identity to two different nodes (`owns`):
  SYS003 kind `directive-directive`. `owner(i)` is Unknown with both
  nodes in `hi`; no downstream rule treats the identity as owned by
  either.
- Two directives bind one flow end to the same identity: not a conflict
  (a duplicate, MDL017-like Advisory from the directive validator).
- A directive that binds identity i to node X while the rank 2 owner of
  i is Must and is a different node Y: SYS003 kind `directive-selector`
  (2.5 gives the exact condition). `owner(i)` stays X, so one wrong
  directive produces one finding, not a cascade.

### 2.2 Source (b): model selectors

For each entity clause that carries a selector, `sel` (grmb-spec 6.4,
owned by gob-walk, G07) yields `Answer<Set<Identity>>` with a status per
identity; B receives one row per identity, status Must for `lo` and May
for `hi \ lo`, and one `hidden(r)` placeholder per unseen remainder. The
rules are exactly those of grmb-spec 6.4 and are only restated where the
binding relation needs them:

1. Must exactly where a literal path would be. A glob is Must for the
   identities whose membership depends only on Must facts (PATH
   membership, a Must containment chain, predicates that evaluated Yes).
   It becomes May along a May or Unknown fact: an edge through an
   unexpanded `phase`, a predicate that evaluated Unknown (an attribute
   the adapter does not provide), a literal path with several candidates.
   Over-approximation is allowed in May rows and never in Must rows
   (universal-model.md 4.4 soundness contract).
2. Containment is Must at F1 and above. A file selector (`"crates/frob/**"`)
   owns every unit the file contains at Must; a unit the adapter could not
   enumerate (a macro, an `opaque` region) is a hidden placeholder, not a
   missing row.
3. F0 artifacts. A file-level selector gives the file's module unit
   at Must; a symbol-level selector (`::qualname`) gives only a hidden
   placeholder on an F0 file, so an F0 file is ownable but its symbols are
   never claimed by a symbol selector.
4. Per-role rows. A selector in `producer` contributes rows with role
   `producer`, one in `owns` role `owns`, and so on. The owner function
   (2.6) reads only `owns` rows, the specificity vectors of grmb-spec 6.5
   and the status of each; every other role is a set.
5. Provenance. Each row records the clause anchor (`node/cli/owns[1]`),
   the matching glob of a compound selector, its specificity vector and
   the chain of facts that gave the status (the `path` field of 1.3).
   `grimble explain <entity-or-symref>` prints it.

Specificity and ties. Specificity is the six-component vector of
grmb-spec 6.5, larger is more specific, and the order is total on
selectors, so the winner never depends on a tool. TIES (two nodes with
the same maximal vector on one identity) make the owner Unknown with
both nodes in `hi`, and SYS002 fires when both rows are Must; a tie is
never broken by file order or name. A tie involving a May row makes SYS002
Unresolved (it may not be a tie), not fired.

Possible-worlds reading of the owner answer (this tightens grmb-spec 6.5
step 2, which compared only equal-specificity May candidates; see 11.3).
Let C(i) be the candidate rows of rank 2 for identity i, each a node with
a specificity vector and a status. Each May candidate may or may not match
in the true program; owner(i) is what the highest-specificity MATCHING
candidate would give in each such world:

- `Exact(Some(X))` iff X is a Must candidate and every other candidate has
  a strictly lower specificity vector (May or Must).
- Unknown with SYS002 iff two Must candidates tie at a maximal vector and
  no candidate has a strictly higher vector.
- Otherwise `Bounds{lo = {}, hi = H}` where H is every candidate not
  dominated by a strictly more specific Must candidate, plus `None`
  (FOREIGN) when no Must candidate exists, plus the hidden placeholder when
  the identity's artifact has an unseen remainder.

### 2.3 Source (c): pack inference

A data pack (grmb-spec section 1; the pack format is G04) may contribute
INFERENCE RULES: declarative rows that propose bindings from names and
attributes. A rule is data, never code or grammar:

```
[[infer]]
id        = "cargo.crate-owns-dir"        # rule id, pack-qualified as cargo::crate-owns-dir
applies   = { entity = "node", attr = "cargo::package" }   # which entities may ask for it
role      = "owns"
from      = { adapter = "cargo-manifest", fact = "package.dir", match = "attr:cargo::package == package.name" }
status    = "may"                          # a rule can never write must
reason    = "a Cargo package owns its directory"
```

1. An entity ASKS for inference with `attr infer = pack::rule_id;` (a
   pack-qualified attribute in the Attr facet). There is no ambient
   inference: with no request, rank 3 contributes nothing (D22, no invisible
   variables), and the inference request is part of the model's digest.
2. A rule's rows have status May and nothing else. Provenance carries the
   pack name and version, the rule id and the names or attributes that
   triggered it (`Inference{pack, pack_version, rule, evidence}`), so every
   inferred row is attributable and pack drift (G04's registry drift-lock) is
   visible.
3. Fill-only. A rank 3 row is admitted for `(e, role)` only where the
   entity has no rank 1 or rank 2 clause for that role, or its clause is
   an inference request. It never adds to, narrows or contradicts a rank 1
   or 2 row. For the function role `owns` the same holds per identity: rank 3
   is consulted for identity i only when ranks 1 and 2 gave no candidate
   (grmb-spec 6.5 step 3).
4. Ties at rank 3 give no owner (May on every tied node) and never a
   finding: inference never creates SYS002 (grmb-spec 10.3 rule 3).
5. Rank 3 never creates a conflict. A rank 3 row against a rank 1 or
   rank 2 row of a different entity is kept as an advisory `overridden`
   fact in provenance (shown by `grimble explain`), never a finding. Only
   Must against Must can be SYS003.
6. Manifest facts. Inference needs facts U does not carry in its term
   (the module name of a PyO3 module comes from `#[pymodule]` plus
   `pyproject.toml`; an assembly directory from an `.asmdef`). They come from
   the F2 manifest adapter (grimble-model.md 9.8): inference that depends
   on a manifest fact is May at best until that adapter exists; where the
   manifest is absent the rule yields nothing and reports no finding (a rule
   that was requested and could not run is `sys-unresolved/inference-unavailable`
   in `grimble explain`, and Unresolved on the rule that needed the row).

### 2.4 Source (d): nothing

Rank 4 is not a source of rows with content; it is the honest
representation of what the other three could not see. It produces:

1. The residual `(e, role, hidden(r), Unknown)` for each unseen remainder r
   of 2.2, so that the Answer's `hi` is never empty merely because the
   adapter lost sight of code.
2. For an identity with no rank 1-3 candidate: `owner(i) = Exact(None)`
   (FOREIGN) if the identity's artifact has no unseen remainder, and Unknown
   otherwise (the identity might be claimed through hidden units, grmb-spec
   10.3 rule 5).
3. For a selector that matches nothing: empty `lo`, empty `hi` if and only if
   nothing was hidden. That is the SYS004 condition and never reads clean
   by default; with a hidden placeholder the rule says Unresolved.

The Unresolved findings that rank 4 causes carry the reason-code family
`sys-unresolved/<reason>`, the one name this file gives to the "SYS-UNRESOLVED"
of grimble-model.md 9.1. It is a reason code family, not a rule id. The
reasons are: `unseen-remainder`, `may-only-owner`, `fidelity`,
`opaque-cone`, `no-detector`, `index-stale`, `inference-unavailable` and
`vacuous`. Findings roll up per rule and artifact by reason, as
universal-model.md 4.2 says.

### 2.5 The merge rule

Input: the rank 1-4 rows for one identity i and one role. Output: the rows
of B and the findings of 2.1-2.4.

1. FUNCTION ROLE (`owns`). The owner is chosen from the rows of the
   strongest rank that has any:
   - rank 1 present: the node of the directive row(s). One distinct node:
     that node, Must. Two distinct nodes: Unknown and SYS003 kind
     `directive-directive`.
   - else rank 2 present: the possible-worlds function of 2.2.
   - else rank 3 present: the node of the rule, May; ties give no owner.
   - else rank 4: `Exact(None)` or Unknown (2.4).
   Rows of weaker ranks are NOT deleted: they stay in B with their
   provenance as `overridden` facts.
2. SET ROLES (`producer`, `consumer`, `shape`, `runnable`, `ref`,
   `evidence`). Membership of i in `B(e, role)` is independent of other
   entities. The row's status is the MAXIMUM status over the ranks that
   produced it (a pair reached by a Must glob and a May glob is Must;
   grmb-spec 10.3 rule 4); its provenance lists every contributing rank,
   strongest first. Rank 3 is fill-only as in 2.3 item 3.
3. THE CONFLICT FINDING (Must against Must, never silent). Let X be the
   node of a rank 1 owner row for i with status Must, and let T be the
   TOP SET of rank 2: the Must candidates at the maximal specificity
   vector among Must candidates of rank 2. Then:
   - if T is empty, or X is in T: no conflict (the directive fills a gap
     the selectors left, or breaks a tie that SYS002 would have reported;
     the SYS002 finding is suppressed because the directive resolved it);
   - if T is non-empty and X is not in T: SYS003 kind `directive-selector`,
     naming the directive site, the clause anchors of T and their
     specificity vectors. The owner stays X.
   A rank 1 Must row against a rank 2 row that is only May is never a
   conflict; it is an `overridden` fact. A rank 2 Must against a rank 3 row
   is never a conflict (2.3 item 5).
4. THE SINGLETON CHECK. For a role that must name exactly one identity
   (`shape`, `runnable`, `ref`): if `lo` holds two or more identities
   the result is SYS003 kind `ambiguous-singleton` naming them (this
   closes the finding id grmb-spec 4.3 reserved as
   `SYS-CONTRACT-AMBIGUOUS`: it is SYS003). If `lo` is empty and `hi`
   is empty the entity has no code (SYS004 for `shape`, SYS011 for
   `runnable` and `ref`).
5. STRUCTURAL CONSISTENCY (kind `end-owner`). For a flow `A -> B` every Must
   identity of `producer` must have `owner = Exact(Some(A'))` where A' is the
   node that resolves from A, and every Must identity of `consumer` the
   node of B, unless the endpoint is an `external` node that owns no code.
   Otherwise SYS003 kind `end-owner` (the model contradicts itself about
   who owns the code a flow end names). May owners give no finding.
6. IDEMPOTENCE AND ORDER. The result does not depend on file order, on the
   order of clauses, or on which file declared what (grmb-spec 3.3). B is
   a set; ties are symmetric.

### 2.6 The final owner function

`owner : Identity -> Answer<Option<Node>>` is the function of grmb-spec
6.5 with the possible-worlds tightening of 2.2 and the merge of 2.5:

```
owner(i) =
  if rank-1 rows exist for (owns, i):    their node (Must), or Unknown + SYS003 if two nodes
  elif rank-2 rows exist:                possible-worlds of 2.2 (SYS002 on a Must tie)
  elif rank-3 rows exist:                the node, May (a tie: no owner, no finding)
  elif i has an unseen remainder:        Unknown
  else:                                  Exact(None)       -- FOREIGN
owner(path) = owner of the module unit of that file
```

### 2.7 Properties

1. Determinism. B is a pure function of (snapshot, model, enabled packs,
   index inputs of section 3). No clock, no network, no live language
   server.
2. Monotonicity in information. Adding a fact (a directive, a more precise
   adapter, an enabled pack) can move a row Unknown to May to Must, and can
   add rows; it never changes a Must row into a row for a different
   entity without a visible source change, because Must rows come only from
   Must facts.
3. Honesty (the instance of universal-model.md Theorem 3). A binding rule
   fires only from `lo` rows (P+) or only when `hi` is empty (P-), and is
   certified clean only from complete `hi` (P+) or a Must row in `lo`
   (P-). A rank 3 row or a hidden placeholder alone can therefore make a
   rule Unresolved, never fire it and never clear it.
4. Locality and incrementality. A row depends on (selector text, the set
   of files matched, the U terms of those files); the cache key is that
   triple's digests, so an edit in one file recomputes only the selectors
   whose file set or matched terms changed (gob-cache; section 8).

## 3. How SCIP and LSP occurrences enter

"The human symref is canonical, SCIP is derived" (grimble-model.md 9.1,
code-model.md section 6): the symref is the name of an identity; a SCIP
symbol is a derived spelling. An OCCURRENCE (a use or definition site
with a symbol, from a SCIP index or an LSP definition or references
response) is one more input to rank 3 and is admitted under these rules.

1. What an occurrence is used for. Occurrences supply two things to B and
   C, and nothing else: (i) the identities an occurrence's symbol maps to
   (resolution of a symref operand that is ambiguous in the scope graph),
   and (ii) reference facts used by builtin inference rules, for example
   `builtin::referrers-of-shape`: for a contract e whose `shape` identity s
   is Must, the referrers of s in artifacts owned by the flow's `to`
   node are candidate `consumer` identities, and the identities that
   construct s in artifacts owned by the `from` node candidate `producer`
   identities. These are rank 3 rows, status May, provenance
   `Inference{pack = builtin, rule = referrers-of-shape, evidence = the
   occurrence sites}`, requested by `attr infer = builtin::referrers-of-shape`
   like every inference.
2. External index: always May. An index produced by an external tool (a
   rust-analyzer or scip-typescript run in a `[[check.tool]]` stage, an LSIF
   or SCIP file checked in or cached) is a May source. It is never Must,
   whatever its content, because the tool is not covered by the adapter
   soundness contract (universal-model.md 4.4) and its notion of
   resolution is its own.
3. Same-adapter index: Must only for what the adapter proves. When gob-ir
   itself exports the SCIP index (the "SCIP derived from U" of code-model.md
   section 6) and the index records the adapter id and version of every
   document, an occurrence whose adapter id and version equal the running
   adapter's takes the STATUS OF THE SCOPE-GRAPH EDGE it was derived from
   (Must stays Must, May stays May). It is upgraded to Must only because it
   is the adapter's own Must edge, not because it is an index. An index with
   a different adapter version, or no version, is treated as external (item
   2) and never upgraded.
4. Staleness. An occurrence is valid only for the file content it was
   computed from. The digest of the document at index time is part of the
   stage's cache key (external) or the export (same-adapter); a document
   whose current file digest differs gives Unknown, with reason
   `sys-unresolved/index-stale`, and the occurrence is dropped from rank 3.
5. Mapping a SCIP symbol to an identity. A SCIP symbol string maps to a
   symref through its descriptors and the document path, then through Q22.
   One candidate: that identity; several: May rows for each; none: the
   occurrence is counted in provenance as unmapped and dropped. SCIP needs a
   package and version for external symbols; an unknown version is written
   as `.` as SCIP allows (grimble-review L2).
6. Anonymous and multi-part units. SCIP is exported only for named units;
   anonymous units are marked `local` (grimble-review L2), so no rank 3 row
   about an anonymous unit comes from an index, and an `Unstable` positional
   identity is never a B anchor for an ack (section 5.5).
7. LSP. A live language-server answer is not admitted in `grimble check`
   (it is not a pure function of the snapshot, 2.7 item 1). The same answers
   are admitted only when materialized as an index file by a pinned tool
   stage (item 2). A live LSP may be used by `grimble explain` and by the
   editor, with every row labelled `live`, and is never an input to a
   finding.
8. Provenance. A row that used occurrences records the index, the tool and
   its version (external) or the adapter id and version (same-adapter), and
   the occurrence sites, so a reviewer can reproduce it.

## 4. The twelve v1 mechanisms

notes/v1/strata.md section 4.1 lists twelve binding mechanisms, B1-B12.
The table maps each to exactly ONE of the four sources (its primary
source; where it also feeds another source, the note says so), gives its
v2 form, its status and what is dropped. Status words: KEPT (same
purpose and form), CHANGED (same purpose, new form or semantics), MOVED
(same purpose, new owner or home), DEFERRED (kept but specified by a later
ticket), DROPPED (no v2 form). The rows record what v1 did; there is no
migration report because `.strata` models are rewritten by hand (D136).

| # | v1 mechanism | What it did | Source | v2 form | Status | What is dropped |
|---|---|---|---|---|---|---|
| B1 | `code "glob"` on node and store | list of fnmatch globs on a node; per FILE; first partition: exactly one owner, else an ambiguity error; none gives FOREIGN | (b) | `owns SEL` rows, role `owns`; real path globs, qualname globs, `kind` and `lang` predicates; the specificity total order; a tie is SYS002; none is FOREIGN, SYS001 | CHANGED | fnmatch semantics (`*` crossing `/`), file-only granularity, "first partition wins", hard error on any overlap (now: the most specific wins), the `store` keyword (a node `kind store`) |
| B2 | `may "atom" [via ..] [of ..]` | capability grant scoped per file, per observation site (symbol `via`), or by `of` first-string-on-the-line argument | (b) | `may ATOM(args) at SEL`: the scope is a selector evaluated by `sel`; rows are queried, not stored in B (1.2); the cell algebra is section 7 | CHANGED | the colon atom form, `of CONSTRAINT`, `via` and `exclusive`; the `of` argument check stays Unresolved until an adapter answers `const_value` (grimble-review M5) |
| B3 | `frob:channel FLOW`, `frob:boundary B`, `frob:secret NODE` | code comment directive: a CHANNEL, BOUNDARY or SECRET edge from the enclosing symbol to a design id; dangling is an error; missing on a boundary is a warning | (a) | `grimble:binds design:flow/F role=producer\|consumer`, `grimble:binds design:boundary/B`, `grimble:channel`, `grimble:boundary` as sugar (2.1 item 4); dangling is SYS003 `dangling-operand` | CHANGED | the `frob:` namespace (frob never reads grimble directives, D28); the blanket "every boundary needs a directive" warning (replaced by SYS009, which is per flow end and only where a selector is empty); `frob:secret` (the clearance of the code that handles a secret is the node's `clearance` and the kernel's label closure; no code-side attestation remains) |
| B4 | frob:doc, frob:ticket, frob:waive, frob:todo comments above a design construct in the .strata file | the .strata file was a frob grammar; each construct a symbol, so frob directives attached to it by regex-located spans | (a) | the F4 `.grmb` adapter: a directive attaches to an entity unit by the position rule of grmb-spec 8.1, a Must row from the directive's own site; frob reads it only through `grimble graph --json` (grimble-model.md 9.3) | MOVED | regex-located spans (the parser has spans), `frob:waive` (now the exception clauses, grmb-spec section 7); a frob without grimble sees `.grmb` as F0 and reports the directive Unresolved |
| B5 | `attr interface=[Sym,...]` | hand-written list of intended public symbol names; SYS108/110 compared it with the real public surface (14 nodes exempt) | (b) | `surface SEL`: a selector, not a name list; the check is SYS014 (reserved, 11.3) | CHANGED | name lists and the hard-coded exempt-node list; a surface is never generated |
| B6 | flows as import permission | `flow A -> B` allowed Python `import` edges from A's files to B's; D-decision: a flow is directed data movement and code edges run with or against it (pulls and pushes), so a flow in either direction between two owners allows the edge, and direction matters for label checks only; FOREIGN endpoints unchecked | (b) | owners come from `owns` rows; the check is a rule over edges between owners (Q28, Q21) and declared flows: SYS013 (reserved, 11.3) in every language that has edges | CHANGED | Python-only `ast` resolution; an edge whose owner is Unknown is Unresolved, never allowed and never denied |
| B7 | marker attrs and a token scan of bound code | `attr timeout;` on a flow or node; a regex such as `\btimeout\s*=` over every file the node owns | (c) | `attr` markers stay (Attr facet); the "does the code honour it" proof is a pack detector rule (reliability pack, G04) that runs over the node's bound identities and yields May evidence with the pack and rule in provenance | MOVED | pooled-file token scanning; the REL2xx-39x families' bespoke Python (moved to pack data, deferred to G04) |
| B8 | `refine X into {...}` and `abstract` | decomposition tree; code binding legal only on leaves; `frob sys plan` frontier | (d) | none: a node that owns nothing is legal (an external system or an unrefined box) and has the residual of an empty clause list, not a binding | DROPPED | the construct (grmb-spec 14.1 item 16); the migration report lists each `refine` and its leaves so the leaves keep their `owns` |
| B9 | vmodel `code_ref "path[:symbol]"` and `runnable "path::Class.method"` | strings attached to a vmodel node; presence checked, resolution left to frob | (b) | `ref SYMREF` and `runnable SEL` rows with roles `ref` and `runnable`; resolved through Q22 and Q35; SYS011 when they resolve to nothing, SYS003 `ambiguous-singleton` when to several | CHANGED | string-only attributes that nothing resolved |
| B10 | `[graph].exclude` in frob.toml | shared exclusion globs for binding, capability scan and the "fully excluded node" skip | (d) | `[grimble] exclude` (materialized, grimble-review M5): excluded files are not in the walk; they are not in I, so they are not FOREIGN and not Unknown, and a selector says nothing about them (grmb-spec 6.4 step 1). It removes identities, which no source can do, hence rank 4 | MOVED | the "fully excluded node" skip (a node whose files are all excluded is just a node whose clause matches no file: MDL005, SYS004 suppressed) |
| B11 | Unity .asmdef generator (T-4512) | generated a root module with one node per asmdef, `code=<dir>/**`, edges from references | (c) | a pack inference rule over the manifest adapter: an asmdef gives an owner for the directory at May, requested by the node's `attr infer` | DEFERRED (G04 for the pack; the manifest adapter of grimble-model.md 9.8) | writing a model file from the generator (the model is never auto-written to match code); the synthetic default assembly |
| B12 | `frob sys init` bootstrap | one node per package directory and one flow per observed import direction, once, never `may` | (c) | `grimble init --propose` prints a skeleton from the same pack rules (names of packages and directories); a human edits it; once edited its clauses are rank 2 | DEFERRED (G18 and the adoption design, grimble-review M10) | any automatic write; flows from observed imports are a suggestion only |

Reading of the table. Every B-mechanism that creates a row of B does so
as rank 1 (B3, B4), rank 2 (B1, B2, B5, B6, B9) or rank 3 (B7, B11, B12);
B8 and B10 create no row and are listed under (d) because their v2
equivalent is the absence of one (the unbound node, the excluded file).
notes/review/grimble-review.md M5 proposed the same mapping by the
words "select queries, annotations, Unresolved"; this table is the
refinement: it gives each mechanism one source and names the rule that
now enforces what the mechanism enforced.

## 5. Identity and rename over time

B is recomputed per snapshot, so "carrying B across commits" means
carrying three things: identities, the lock entries keyed by them, and
the decisions a human recorded about them.

### 5.1 What anchors an identity

- Entity: `(module, full name)` (grmb-spec 5.5). Moving an entity between
  files of the same model keeps its identity. `alias` names are permanent
  alternative spellings of the same identity; `renamed_from` names are
  transitional and resolve with MDL012.
- Code unit: `(symref, unit kind)`, where the symref is
  `<locator>::<qualname>` of code-model.md section 2. The symref moves when a
  file moves or a symbol is renamed; the digests do not define identity.
  A multi-part unit has one identity whose Body facet is the ordered
  composition of its parts. An anonymous unit's identity is the enclosing
  symref plus the positional index computed on the alpha-normal form
  (universal-model.md 2.6); it is `Unstable` (5.5).

### 5.2 What is carried

| Thing | Carried by | Keyed by |
|---|---|---|
| a recorded digest of a bound identity | `grimble.lock` symbol entry (gob-lock, typed entries, G05) | identity anchor and facet |
| the digests of a flow's two ends | `grimble.lock` flow entry: flow key, role, the end identity, `end_contract` (the Contract facet of the end symbol) and `shape_contract` (the Contract facet of the contract entity's shape) | flow identity and role |
| an entity's own Body digest at ack | `grimble.lock` symbol entry with `kind = entity` | entity identity |
| a rename decision | `grimble.lock` ack_log entry of kind `rename` and the lock's `renamed` chain `old anchor -> new anchor` | old anchor |
| an exception (accept, defer, hotfix) | the clause or the exception record; the target is an entity (logical location) or an identity | entity identity or identity anchor |

The lock never stores B rows. A row at the time of an ack is derivable:
the lock stores the digests the human attested, and the next check
recomputes the rows, so a binding that changed (a selector now matches
other identities) is not drift by itself; the digests of the identities
the ack covers are what SYS006 and SYS007 compare.

### 5.3 What an ack means for B

`grimble ack <target>` is a human attestation over a set of rows, with a
mandatory reason (as `frob ack`). It records, for each acked
`(e, role, i)`, the facet digests of i at that moment. The rules of what
an ack may cover follow from honesty:

1. Only Must rows with Exact facets can be acked. An ack of a May row or of
   an identity whose facets are Unknown (an F0 or F1 language, an
   `opaque-cone`) is refused with the list of rows, because the tool cannot
   see what a human would be attesting. This is why the P0 rules of section 6
   are never Unresolved for an acked entry in the normal case: an entry
   exists only if it was Exact.
2. Acking an entity role covers the identities of its flow ends and its
   `shape` (the entries needed by SYS006); ownership of a whole directory
   is not digest-locked by default, because `owns "crates/gob-*/**"`
   legitimately grows (a new crate is a new identity under the glob, not
   drift). Locking a specific symbol of a node is `grimble ack <symref>`.
3. An ack is evidence about the digest, not a permanent claim about the
   binding: if the row later becomes May or Unknown (the adapter lost
   precision), the P0 rules go Unresolved with the fidelity reason; the
   entry is not discarded.
4. A scheme change (digest scheme, or the `.grmb` language major) makes every
   entry stale with the recorded reason (grimble-model.md 9.2, grmb-spec 3.4),
   which is SYS007 with kind `scheme` and not a re-key.

### 5.4 Rename: the heuristic

A rename of an identity i0 is a new identity i1 whose Body facet equals
the Body of i0, where i0 is gone from the snapshot (SYS008 shape,
grimble-model.md 9.2). To make it cheap and deterministic:

1. Detection scope. Only lock entries are examined (an identity nobody
   acked has no history to carry); `at_revision(rev)` and
   `diff_symbols(old, new)` (Q43) give the Gone and New sets exactly.
2. Candidate set. For each Gone anchor with entries: the New identities
   with the same unit kind and the same language and a Body digest equal to
   the recorded one (`by_digest(Body, d)`, Q42). Sig is deliberately not
   compared: the name is in Sig, and a rename changes it.
3. Trivial bodies. A Body with fewer than `[grimble] rename_min_tokens`
   tokens (default 12; open question 11.2.10) cannot be paired: an empty
   function body or `return None` matches everything. Such an identity is
   reported Gone (SYS007 kind `gone`), not renamed.
4. Status. One candidate: a May pairing with provenance `Inference{rule =
   body-facet-match, unique}`. Several candidates: May for each; SYS008
   lists them and never picks one. Extra evidence (same parent directory,
   same enclosing type, same Doc facet) only orders the display. The pairing is
   May even when unique, because digest equality of Body does not prove
   the same intent (a copied function and a deleted original).
5. Reporting. A Gone anchor with at least one candidate is SYS008 (Advisory,
   with the suggestion to run `grimble ack --rename OLD NEW`) and NOT
   SYS007: one root cause, one finding. A Gone anchor with none is SYS007
   kind `gone`.
6. Moves of whole directories. If at least `[grimble] rename_min_group`
   (default 5) pairings share one old-prefix to new-prefix mapping, they
   are reported as one finding naming the prefix mapping and the count, and
   `grimble ack --rename-prefix OLD/ NEW/` applies them together.
7. What the heuristic does not touch. Entities with `renamed_from` are paired
   deterministically (Must, declared); an entity rename without
   `renamed_from` uses items 1-5 on the entity's Body facet, except that
   an entity pairing is only offered when the entity kind and the full name
   prefix agree.

### 5.5 What an ack of a rename means

`grimble ack --rename OLD NEW`:

1. verifies the pairing is still May-or-better (OLD still absent, NEW
   present, Body equal) and records an ack_log entry of kind `rename` with
   the reason, actor and date;
2. migrates the lock entries of OLD to NEW (re-keyed, digests kept) and
   adds `OLD -> NEW` to the lock's `renamed` chain, so that a check run
   at an older revision or an exception that still names OLD resolves
   through the chain (exceptions follow the chain; a bare symref that does
   not resolve is reported with the chain's suggestion);
3. after the ack the pairing is a recorded decision, and the digests of NEW
   are compared as a normal entry: if NEW's body differs from the acked body,
   that is SYS007, so a rename that also edits the body is detected at
   the next check, never absorbed;
4. never edits code or a model file (the v1 "suggest, never edit" rule); the
   one file it writes is the lock.

For entities the equivalent is the ack planner migrating the entries of the
`renamed_from` name (grmb-spec 5.5); both paths append to the same
ack_log.

UNSTABLE identities. An identity whose anchor is positional (an anonymous
unit; a cell of a notebook with nbformat before 4.5, which has no stable
cell id) is `Unstable`: it has rows in B, it can be reported on, it is
refused as a lock key (lint-requirements.md section 6 item 2, the
notebook example), and the P0 rules do not apply to it (NotApplicable, not
Unresolved: the language declares it cannot have a stable key). The nearest
named container is the key: a lock entry for a cell with no id is a
file-level entry.

## 6. The drift and binding rules over B

This section restates grimble-model.md section 4's drift table as
predicates over B, the facets and the scope graph. The ids SYS001-SYS012
are the ticket's set; they differ from the ids of grimble-model.md
section 4 and grmb-spec in places, and 11.3 gives the exact mapping and the
two ids (SYS013, SYS014) reserved for the rules that no longer fit the
twelve. Every rule is generated once with the `Rule` derive in
`grimble-bind` (ownership and binding rules, G11; the drift rules SYS006-SYS008
and the reserved ids G12; SYS012 is a matrix-build rule owned by G14; the exact split is the implementation tickets').

Every rule declares polarity (universal-model.md 4.2). A rule evaluated
over a subject whose answer is Unknown reports Unresolved, never clean; a
subject that is NotApplicable is excluded from the subject set; a rule
that examined zero subjects over a scope that was not wholly NotApplicable
reports Unresolved("vacuous"), required when the rule is flagged
`must_measure` (cli.md section 2). An `accept` cannot park an Unresolved
finding (EXC016).

Severity column: proposed defaults; Warn rules become Error under
`[grimble] strict = true` where the table says "strict".

| Id | Alias | Polarity | Severity | Subject | `must_measure` |
|---|---|---|---|---|---|
| SYS001 | SYS-UNOWNED | P- | Warn (strict: Error) | an artifact in the walk | no |
| SYS002 | SYS-AMBIGUOUS-OWNER | P+ | Error | an identity with two Must owners tied | no |
| SYS003 | SYS-BINDING-CONFLICT | P+ | Error | a binding row set or an operand | no |
| SYS004 | SYS-ENTITY-WITHOUT-CODE | P- | Warn | a binding clause of an entity | no |
| SYS005 | SYS-UNMODELED | P+ | Warn (strict: Error) | a unit in a `modeled` selector | yes |
| SYS006 | SYS-CONTRACT-SKEW | P0 | Error | a flow with a contract and acked ends | yes |
| SYS007 | SYS-CHANGED | P0 | Error | a lock entry | yes |
| SYS008 | SYS-RENAMED | P0 over the Body digest, May pairing | Advisory | a Gone anchor with entries | no |
| SYS009 | SYS-FLOW-END-UNBOUND | P- | Warn | a flow end | no |
| SYS010 | SYS-CLAIM-WITHOUT-EVIDENCE | P- | Warn | a claim above L1 | no |
| SYS011 | SYS-VMODEL-LINK-BROKEN | P- | Error | a vmodel `ref` or `runnable` | no |
| SYS012 | SYS-EXCUSE-GRANT | P+ | Error | a template excuse and an atom | no |
| SYS013 | SYS-UNDECLARED-FLOW | P+ | Error | an import or call edge of the symbol graph | no |

### 6.1 SYS001 unowned (P-)

- Subject: each artifact in the walk that is not excluded by `[grimble]
  exclude`. The model's own `.grmb` files are artifacts and are ownable like
  any other.
- Frob-owned artifacts are not subjects. frob's own files belong to no
  node of the design model, so asking whether a node owns them is
  vacuous. They are excluded from SYS001's universe (and from its subject
  count) rather than given an implicit owner: an implicit `frob ledger`
  node would put a model entity the user never wrote into the owner
  function, SYS002 ties, `bindings` rows and acks, and would still need
  the owned set passed in. The exclusion needs no change to `gob.sibling/1`:
  grimble reads the one configurable path itself from the shared
  `frob.toml`. The frob-owned set is final and closed:
  - the ledger directory, `[tickets] dir` of `frob.toml` (default
    `tickets`), everything under it, matched by whole path components;
  - `changelog.d/`, the release fragments;
  - `frob.lock`, frob's ack lock;
  - `.frob/`, frob's per-worktree local state.

  Every other unowned file is still reported, including `grimble.lock`
  and the model's own files. The set is `grimble_bind::frob_owned`.
- Predicate: `owner(i) = Exact(None)` for EVERY unit i of the artifact,
  including its module unit; that is, no node owns any part of it. An
  artifact some node owns in part is not SYS001 (the unowned remainder is
  SYS005's concern where modeled).
- Fires: the good thing (an owner) is not in `hi`: the artifact has no
  unseen remainder and every unit is `Exact(None)`.
- Certified clean: some unit has an owner in `lo` (Exact(Some(n))).
- Unresolved: some unit's owner is Bounds with a May-only owner
  (`sys-unresolved/may-only-owner`); the artifact has an unseen remainder
  (`unseen-remainder`); the artifact is F0 and only a symbol selector could
  own it (`fidelity`).
- Granularity: one finding per artifact, rolled up by directory in the
  report, so a repository with ten thousand unowned files is one line per
  directory, not ten thousand.
- Dedup: SYS005 subsumes SYS001 for any artifact under a `modeled`
  selector (one root cause, one finding).
- Required mark: none; unowned code is a model completeness question
  (FOREIGN is Warn until `[grimble] strict`, grimble-model.md section 8).

### 6.2 SYS002 ambiguous owner (P+)

- Subject: an identity i.
- Predicate: two nodes X and Y such that both have a Must row of rank 2 for
  i, both at the maximal specificity vector among all rank 2 candidates of
  i (2.2), and no rank 1 row exists for i.
- Fires: the pair is in `lo` (both Must). The finding names both clause
  anchors and the shared specificity vector. `owner(i)` is Unknown.
- Certified clean: no tie is possible in `hi`.
- Unresolved: a tie that includes a May row (`may-only-owner`): the tie
  may not exist.
- Suppressed when a rank 1 directive names one of the tied nodes (2.5
  item 3: the directive resolved the tie).
- Required mark: none.

### 6.3 SYS003 binding conflict (P+)

One rule with a `kind` attribute on each finding. All kinds fire from `lo`:

| Kind | Predicate | Notes |
|---|---|---|
| `directive-directive` | two rank 1 rows for one identity and role `owns`, two different nodes | `owner` is Unknown |
| `directive-selector` | 2.5 item 3: a rank 1 Must owner X not in the top set of the Must rank 2 candidates | `owner` stays X |
| `ambiguous-singleton` | `lo(e, role)` has at least 2 identities for `shape`, `runnable` or `ref` | covers the id grmb-spec 4.3 reserved |
| `end-owner` | a Must `producer` (or `consumer`) identity of flow `A -> B` has owner Exact Some(n) with n not the node of A (of B), excluding `external` endpoints | the model contradicts itself |
| `dangling-operand` | a `grimble:binds` entity operand names no entity, or a symref operand resolves to nothing | the v1 dangling-directive error |
| `ambiguous-operand` | a symref operand has several candidates | rows are May for each |

- Unresolved: the identity's owner is only Bounds (the conflict may not
  exist) for `end-owner`; the operand resolution is Unknown because the
  target artifact is F0 or opaque (`unseen-remainder`) for the operand kinds.
- Required mark: none; a conflict is a loud finding, not a measurement.
- Dedup: a `directive-selector` on identity i suppresses SYS002 for i.
- Exceptions: an `accept` of SYS003 is legitimate only on `directive-selector`
  (a reviewed override, with a reason naming why the selector cannot be
  changed); the EXC budget rules apply.

### 6.4 SYS004 entity without code (P-)

- Subject: one binding CLAUSE of an entity, identified by its anchor
  (`node/cli/owns[1]`): each `owns` of a node, `producer` and `consumer` of a
  flow, `shape` of a contract, `runnable` of a vmodel, `ref` of a vmodel
  that names a code unit, `evidence tests` of a claim. A node with no
  `owns` is not a subject (an external system); a flow with neither a
  `producer` nor a `consumer` clause has two subjects that both fire as one
  finding ("flow without code").
- Predicate: `hi(e, role)` restricted to that clause's rows is empty (no
  Must, no May, no hidden placeholder).
- Fires: `hi` is empty. This is the old SYS001 "selector matches zero
  symbols" of grimble-model.md section 4, now per clause.
- Certified clean: `lo` of the clause holds an identity.
- Unresolved: `hi` holds only May rows or placeholders (the selector
  matches files that hide units, or an F0 file under a symbol selector).
- Suppressed: when the clause's PATH matches no file in the walk, MDL005 (Warn)
  already says so and suppresses this finding (grmb-spec MDL005): a selector
  naming code that does not exist yet is a model describing the future, one
  warning, not two.
- Both flow ends empty: SYS004 once per flow; one end empty and the other
  not: SYS009, not SYS004.
- Required mark: none.

### 6.5 SYS005 code without entity (P+, opt-in)

- Subject: each unit u of the identities selected by the `[grimble] modeled`
  selector list (grimble.toml). When the list is empty the rule has no
  subjects and is not run; there is no repo-wide default.
- Predicate: u is in `lo(modeled)`; `visibility(u) = Yes public` OR
  `effects(u)` has an atom in its `lo`; AND `owner(u) = Exact(None)`.
- Fires: an offender is in `lo` (u's public or effectful status and its
  lack of owner are both Exact). The finding names the first atom or the
  visibility and points at the unit.
- Certified clean: no offender in `hi`.
- Unresolved: `visibility(u)` is Unknown and no effect is in `lo`
  (`fidelity`); `owner(u)` is Bounds containing `None` (`may-only-owner`);
  `u` is in `hi(modeled)` but not `lo` (the modeled selector is May on it).
  NotApplicable: a language with neither visibility nor effects (a CSS file
  has effects `net` impossible and no visibility): the unit leaves the subject set.
- Required mark: yes. `must_measure`: with `modeled` non-empty, if every
  selected unit has Unknown visibility and no effect answer (all F1), the rule
  examined zero subjects and its vacuous Unresolved is required, so opting in
  to a check the languages cannot measure is a gate failure, not a quiet pass.
- Dedup: subsumes SYS001 for artifacts under `modeled`.

### 6.6 SYS006 contract skew (P0)

- Subject: a flow F with a `contract` clause naming contract K, whose
  producer and consumer ends each have a `grimble.lock` flow entry.
- Predicate. Let `S_live = Contract(shape(K))` (the Contract facet of K's one
  `shape` identity), `S_p` and `S_c` the `shape_contract` digests recorded
  in the producer and consumer entries. P0: when all three are Exact,
  - fires if `S_p != S_c` (the two ends were attested against different
    versions of the contract) or `S_live != S_p` or `S_live != S_c` (the
    contract changed since an end was acked: that end is behind);
  - the finding names which end is behind and both digests.
  - certified clean if the three are equal.
- Unresolved (P0 needs Exact on every side): `S_live` is Unknown, Absent or
  touches an opaque cone (`opaque-cone`); the shape identity's language is
  F0 or F1 (`fidelity`: the Contract facet needs the normalized signature);
  the shape row is May (`may-only-owner`: it is not known which identity
  the contract names).
- Not applicable (not Unresolved): a flow with no `contract`, or with only
  one end acked (no skew can exist: SYS009 or an "unacked" line in
  `grimble status`, not a finding here).
- Versioning: `versioning compat=` of the contract (grmb-spec 4.3) says what
  skew is ALLOWED to be: with `compat=backward` and a consumer ack behind,
  the finding is Warn (the producer may have moved forward); with
  `compat=none` or unspecified it is Error. The versioning attributes never
  change whether skew exists, only its severity.
- Required mark: yes (`must_measure`): an acked flow whose every contract
  facet became Unknown (a language downgrade) must not pass.

### 6.7 SYS007 changed since ack (P0)

- Subject: a `grimble.lock` entry (symbol, entity or flow end).
- Predicate. For each acked facet f of identity i (Sig, Body, Doc, Attr, and
  Contract for flow ends): `Facet(i, f)` live against the recorded digest.
  Both Exact and different: fires. Both Exact and equal: clean.
- Kinds: `facet` (a digest differs), `gone` (the anchor is absent and has no
  SYS008 candidate, 5.4), `scheme` (the recorded `digest_scheme` or `.grmb`
  major differs: every entry is stale with the recorded reason, never
  re-keyed).
- Unresolved: `Facet` is Unknown (F0 or F1 language: `fidelity`; the facet's
  stream touches an `opaque` or `hole`: `opaque-cone`); for `gone`, a
  same-language artifact that is new since the ack has an Unknown Body digest
  and could hold the moved identity (`opaque-cone`).
- NotApplicable: an Unstable identity (5.5) has no entry; an entry that SYS008 reports.
- Required mark: yes (`must_measure`): all entries Unknown after a fidelity
  change is the failure the ack was meant to prevent.
- The exception state `REATTEST` (exceptions.md) is evaluated by the same
  digest comparison and is not a separate rule.

### 6.8 SYS008 renamed (May heuristic, Advisory)

- Subject: a Gone anchor with at least one lock entry.
- Predicate: 5.4: `by_digest(Body, recorded)` over the New identities of the
  same kind and language is non-empty and the Body is not trivial.
- Fires: Advisory only, with the candidates and the command that accepts one.
  The pairing is May, so the rule is not P0 in effect: it never changes the
  state of an entry (SYS007 does not fire for it) and it never blocks a gate
  at the default `--fail-on`.
- Unresolved: the New set contains a same-language identity whose Body digest
  is Unknown (`opaque-cone`), so a candidate may be hidden; reported once, not
  per anchor.
- Required mark: none.

### 6.9 SYS009 flow end unbound (P-)

- Subject: a flow end (role `producer` or `consumer`) where the flow's endpoint
  node owns code (the node has an `owns` clause; an `external` node or a node
  with no `owns` is exempt, since nothing could bind).
- Predicate: `hi(F, role)` is empty for this end while `lo(F, other role)` is
  non-empty (the other end is bound). If both ends are empty: SYS004 for the flow.
  If the flow has a missing clause for the end (no `producer` clause at all)
  it is the same as an empty `hi`.
- Fires: `hi` empty (this is the old SYS005, "producer or consumer selector
  empty"). The finding names the missing end and the endpoint node.
- Certified clean: `lo` of the end holds an identity.
- Unresolved: `hi` holds only May or hidden rows (`unseen-remainder`,
  `fidelity`).
- Required mark: none.

### 6.10 SYS010 claim without evidence (P-)

- Subject: a claim with `proof` above L1 (the default `[grimble] default_proof`
  if no clause) that is not `assumed`.
- Predicate: `hi(claim, evidence)` has no test unit. `evidence ref` rows
  (document anchors) count as evidence for the purposes of this rule only
  when the claim's proof rung allows a document (G03 states the ladder;
  until then any resolved row counts).
- Fires: `hi` empty or every row resolves to a unit that `test_items` says is
  not a test (the "evidence" is not runnable).
- Certified clean: `lo` holds a test unit (or an allowed anchor).
- Unresolved: `test_items` is Unknown for the language (`fidelity`), or the
  evidence rows are May (`may-only-owner`).
- NotApplicable: the language of the selected units has no test convention
  (`test_items` NotApplicable): those units leave the subject set; if the
  whole evidence set leaves it, the finding is Unresolved("vacuous"), not clean.
- Relation to the kernel: the kernel's UNPROVABLE verdict for the same claim
  (grmb-spec 8.3) is the same root cause; SYS010 is the finding and the verdict
  remains in the status output (one root cause, one finding; open question
  11.2.12).
- Required mark: none.

### 6.11 SYS011 vmodel link broken (P-)

- Subject: a vmodel `ref` (artifact) or `runnable` (test).
- Predicate: `hi(v, ref)` or `hi(v, runnable)` is empty: the document anchor
  does not exist (Q22 NotFound over the document's slugs) or the runnable
  names no test unit. Several test units is SYS003 `ambiguous-singleton`.
- Fires: `hi` empty and the target artifact (a document or a test file) is
  in the walk and not opaque.
- Certified clean: `lo` holds exactly one identity of the right kind.
- Unresolved: the artifact is F0 and the link names a symbol in it
  (`fidelity`); `test_items` Unknown (`fidelity`).
- Not this rule: a link between vmodel entities that is ill-formed
  (MDL014) and the five kernel closure rules (G03, G16).
- Required mark: none.

### 6.12 SYS012 template excuse contradicts a grant (P+)

D75 redefines this rule. It is a matrix-build check implemented in G14
(grimble-capabilities), not in G11 with the other SYS rules; the id stays
in this family because it was already allocated. Before D75 it checked a
node-level `excuses` clause against that node's own grants. Node-level
excuses no longer exist (grmb-spec 4.8, MDL018), so the rule now checks a
matrix-build TEMPLATE excuse (grmb-spec 4.7, packs.md 6.7) against the
grants of the model.

- Subject: a template excuse `excuse A for S` (from a `template` entity or
  an enabled pack) and a grant `may A' at G` of some node n in the model.
- Predicate: A' overlaps A in the atom hierarchy (`A` equals A', is an
  ancestor of A' as `fs` of `fs.read`, or a descendant) AND the excuse
  selection `S` overlaps the grant scope (the grant's `at` selector, by
  default n's `owns` set): some unit is in both `sel(S)` and the grant
  scope, or the overlap cannot be shown empty. All of these are facts of
  the model and the pack: no code is read and no detector can be Unknown
  (the atom must be known: an atom in no registry is MDL016 and the
  excuse is then not a subject).
- Fires: the excuse and the grant are both in `lo` (model facts, always
  Exact). The finding names the template, the excuse, the node and the
  grant and which to remove: the template says the atom does not apply to
  that code, the grant says the node may use it, and both cannot hold.
- Certified clean: no overlapping (excuse, grant) pair exists.
- Unresolved: never, for a known atom. (An overlap that depends on an
  attribute unknown at the adapter's fidelity is decided conservatively
  as overlapping: the contradiction is reported, because the rule reads
  model facts only and a possible overlap is itself a model defect.)
- Why this rule exists: a template excuse and a grant for the same code
  and atom would make the matrix cell ambiguous (section 7) and let the
  excuse's reason hide a real grant. It is the model-side twin of CAP004,
  which catches the same contradiction against OBSERVED use.
- Not this rule: a use observed in excused code is CAP004 (grimble-model.md
  section 4), not SYS012.
- Required mark: none.

### 6.12a SYS013 undeclared flow (P+)

- Subject: one Imports or Calls edge of the snapshot's symbol graph (gob-symbols:
  TS and TSX imports, calls and JSX component uses, Python, C# and Rust calls),
  read through the same owners and flows as every other rule; there is no
  language-specific path.
- Predicate: both ends are owned at Must by different nodes A and B, the edge
  is Must, and no flow connects A and B in either direction (B6: a flow is
  directed data movement, grmb-spec 4.2, and code edges run with or against
  it, so direction matters for label checks only).
- Fires: once per ordered owner pair, listing the edges (Error).
- Certified clean: the edge is inside one owner, or a flow in either direction between the two owners declares it.
- Not checked: an end no node owns (FOREIGN) and an import of a package outside
  the repository.
- Unresolved (`unresolved-edge`): the edge is May, or Unknown with no target
  (dynamic callee, unbound name); (`may-only-owner`): an end is owned only at
  May or its file hides what owns it. One finding per reason and owner, with
  the count; an Unknown edge is never clean.
- Not applicable: fewer than two nodes that own code, or no edge in the snapshot.
- Required mark: none.

### 6.13 Summary of conditions

| Condition | Meaning | Rules that report it |
|---|---|---|
| `unseen-remainder` | a matched artifact holds opaque, hole, phase or an unreadable file | 001, 003, 004, 009 |
| `may-only-owner` | the owner or row is May only | 001, 002, 003, 005, 006, 010 |
| `fidelity` | F0 or F1 language for a facet or capability the rule needs | 001, 004, 005, 006, 007, 009, 010, 011 |
| `opaque-cone` | the facets or edges the rule reads touch opaque or hole | 006, 007, 008 |
| `no-detector` | no detector for an atom in a language | (section 7, CAP rules) |
| `index-stale` | an external or exported index no longer matches the file digest | any rule reading a rank 3 row |
| `inference-unavailable` | a requested inference rule lacked its manifest fact | any rule reading that row |
| `vacuous` | zero subjects over a scope that was not wholly NotApplicable | 005, 006, 007 (required), 010 |

## 7. The capability matrix as a view over B

grimble-model.md 9.6 defines the cell set once: uses, undeclared,
declared-unused, denied (blank), excused (template only), not-applicable and
unknown. This section defines
the matrix as a VIEW over B: how a cell is computed from the bound identities,
without storing it, so that the CAP rules (G14) and `grimble status` are one
computation.

### 7.1 The subject sets of a node

For node n and atom a:

- `M(n)`: identities with `owner(i) = Exact(Some(n))` (Must-owned).
- `Y(n)`: identities with n in `hi(owner(i))` but not `lo` (May-owned).
- `H(n)`: the hidden placeholders of n's `owns` clauses (unseen remainder).
- `Grants(n, a)`: the identities in the scope of every `may A' at SEL` clause of
  n with A' covering a (hierarchy: `fs` covers `fs.read`), through `sel`; the
  default scope is `M(n)`.
- `Det(i, a) = detectors(L(i), a)`: NotApplicable | None | Some(precision).
- `Use(i, a) = effects(i)` restricted to a: an Answer over EffectSites; `Use_lo`
  Must uses, `Use_hi` possible uses.

Note that ownership is `owner(i)`, not "the identity matched n's selector":
an identity matched by `owns "crates/frob/**"` but owned by a more
specific node m counts for m (2.2).

### 7.2 The cell

The cell of `(n, a)` is computed, in this order:

1. Row exemption. If `M(n) U Y(n) U H(n)` is empty (the node owns no code:
   an external system), every cell of the row is `not-applicable` with reason
   `no-code`, and the row is excluded from the summary Unresolved.
2. Applicability. Partition `M(n) U Y(n)` by language. If `Det(L, a)` is
   NotApplicable for every language present: `not-applicable`. Identities of a
   language with NotApplicable leave the subject set for the rest.
3. Observed uses, BEFORE any excuse. Let `E(n, a)` be the identities of the
   remaining subject set covered by a template excuse for a' covering a
   (grmb-spec 4.7, packs.md 6.7); it is empty when no template applies. If
   some `i` in `M(n)` has `Use_lo(i, a)` non-empty:
   - `i` not in `E(n, a)` and covered by a grant at i (`i` in `Grants(n, a)`
     Must): the cell is `uses`.
   - `i` not in `E(n, a)` and not covered by a grant: the cell is
     `undeclared` (CAP001 fires: P+ from `lo`). Deny by default: an ungranted
     atom is denied, so the observed use is the finding.
   - `i` in `E(n, a)`: the cell is `uses` and CAP004 fires (P+ from `lo`,
     Error) instead of CAP001 for that use (one root cause, one finding),
     whether or not a grant also covers it. An excuse never masks an
     observed use.
4. Unknown and uncertain. If any remaining language has `None`, or any
   remaining identity has `Use` Unknown, or `H(n)` is non-empty: the cell is
   `unknown` unless a `lo` use already decided it (item 3). When the
   uncertain identities are in `E(n, a)` (a May or Unknown use there, a
   missing or unavailable detector, F0 or F1 fidelity, an opaque cone), CAP004
   is Unresolved for them with the reason of the failed condition and the
   cell is `unknown`, never `excused`: an excuse is not evidence of absence.
5. Excused. If `E(n, a)` is non-empty and items 3 and 4 did not decide the
   cell, the identities of `E(n, a)` leave the subject set for the rest of the
   computation (their detection was complete and found no use). When every
   remaining identity is in `E(n, a)` the cell is `excused` (with the
   template name and reason). A template excuse that overlaps a grant `may A'`
   is SYS012 (6.12) and does not change the cell.
6. Declared-unused. If `Grants(n, a)` is non-empty and the whole grant scope
   is Must-owned, detector-covered (`Some`) and complete: `Use_hi` over the
   scope is empty: `declared-unused` (CAP002 fires: P-, Exact absence only,
   which is also the only case `grimble shrink` acts on).
7. Otherwise, with no grant and no use: the cell is `denied` (shown blank).
   Capabilities are denied by default (D75): a blank cell is a decision, not
   "not yet considered", and it raises no finding. CAP003, which used to
   report such a cell, is retired. The only finding on a denied atom is
   CAP001 when a use is observed (item 3).

Effect of May ownership. A use found at an identity in `Y(n)` is in `Use_hi`
of n and not in `Use_lo`: it can prevent `declared-unused` (a use might
exist), make `undeclared` Unresolved (not fired) and never create `uses`.
Over-approximated ownership is thus legal for P- cells and illegal as the sole
basis of a P+ finding, exactly the table of universal-model.md 4.2.

Unresolved accounting. The summary carries one Unresolved per node for its
`unknown` cells (not per cell), reason `no-detector` or `fidelity`, so an
unmeasured node never reads as clean (grimble-model.md 9.6).

### 7.3 The not-applicable declaration

NotApplicable is declared by the detector registry, never by a model file.
A detector row with `detector_kind = none` and `impossible = true` for
`(language, atom)` declares the capability impossible there (CSS has no network;
a Markdown file has no `exec`); the declaration carries a reason, is data
in a pack or in gob-ir (G14, G04), and surfaces as the answer
`detectors(lang, atom) = NotApplicable`. A model cannot declare an
atom not applicable and cannot excuse one on a node. Excuses exist only in
matrix-build templates (grmb-spec 4.7, packs.md 6.7), each with a mandatory
reason, listed and counted in `grimble check --json`, and an excuse never
hides an observed use (CAP004, 7.2 item 3), so a model can never hide a
measured or unmeasured cell by asserting impossibility or exemption. `not-applicable` is reported in
the matrix and is never Unresolved.

### 7.4 Aggregation across languages

A node with Rust and Python identities has per-language detector answers; the
cell above is the aggregate. The matrix report shows, for each cell, the
per-language breakdown on demand (`grimble explain node/cli fs.write`), with
each contributing identity, its owner row (rank and status) and its detector
precision (Typed or Lexical, grimble-model.md 9.6). A `Lexical` precision
use is in `Use_hi` only for P+ purposes unless the detector row declares it
Typed.

## 8. Queries grimble-bind needs from gob-ir and gob-walk

Names are the proposal of this design; the answer forms follow
universal-model.md 4.1 (Exact, Bounds, Unknown, NotApplicable). G07 (selectors)
and the gob-ir ticket expose them; the numbers are the Q-ids of
universal-model.md section 5 where one exists.

### 8.1 gob-walk (G07)

| Query | Signature in prose | Answer | Notes |
|---|---|---|---|
| `Selector::parse` | selector text and the base span of that text in its file, giving a `Selector` or a list of syntax errors with spans mapped back into the file | Result | grmb-spec 6; spans offset-corrected; the escapes of a string literal are mapped through a source map (11.1 question 3) |
| `sel` (Q32, first half) | a `Selector` and a snapshot, giving the identities with a status each plus the hidden placeholders | Bounds over `(Identity, Status)` and `Hidden(artifact, reason)` | grmb-spec 6.4; `hi` includes the placeholders, `lo` never |
| `match_table` | a list of `(Key, Selector)` pairs and a snapshot, giving for each identity the rows `(Key, status, specificity vector, which glob matched, path of facts)` and per Key the hidden list | one pass | the only way to evaluate all `owns` selectors at once; grimble-bind implements the owner merge on it; the generic part stays in gob-walk so leases and crunk can reuse it (grimble-review M12) |
| `specificity` | a `Selector` and one of its matching globs, giving the six-component vector of grmb-spec 6.5 | Exact | total order; a compare function is exported |
| `literal` | a `Selector`, giving a symref text if it is a LITERAL selector | Option | grmb-spec 6.4 item 5 |
| `by_construction_empty` | a `Selector`, whether it can match nothing whatever the repository holds | Yes or No | MDL010 |
| `unseen` | an artifact, giving the reason it hides units (opaque, hole, phase, F0, unreadable, oversized) | Option of reason | the source of hidden placeholders |

### 8.2 gob-ir and the adapters

| Query | Signature in prose | Answer form | Used for |
|---|---|---|---|
| `resolve_symref` (Q22) | symref text, giving one identity, candidates or not-found | One, Ambiguous, NotFound | directive operands, vmodel `ref`, evidence `ref` |
| `symbols(a)` (Q04) | an artifact, giving its units | Exact or Bounds | SYS001, SYS005 subjects |
| `kind(u)`, `visibility(u)` (Q06, Q07) | a unit | Exact; Yes, No, Unknown, NotApplicable | predicates, SYS005 |
| `attributes(u)` (Q08) | a unit | Exact | `attr(...)` predicate; pack inference triggers |
| `facet_digest(i, f)` (Q38) | an identity and a facet | Exact, Absent or Unknown | SYS006, SYS007 |
| `contract(i)` (Q39) | an identity | Exact or Unknown | SYS006 |
| `by_digest(f, d)` (Q42) | a facet and a digest | the identities | SYS008 |
| `at_revision(rev)`, `diff_symbols(old, new)` (Q43) | two revisions | Exact lists of New, Gone, Sig, Body, Doc, Attr changes | SYS007, SYS008 |
| `parse_status(a)`, `opaque_regions(a)` (Q02, Q17) | an artifact | Exact | unseen remainder, opaque cone |
| `fidelity(lang)` | a language tag | Exact level F0-F4 and the capability cells | the `fidelity` condition |
| `contains(u)`, `parent(u)` (Q27) | a unit | Exact | the containment chain of 2.2 |
| `edges(u, kinds)`, `referrers(t, kinds)` (Q28, Q29) | a unit | Bounds with status | `end-owner`, SYS013, occurrences of section 3 |
| `binds(u)` (Q36) | a unit | Bounds over C edges | cross-language reach (grimble-bind supplies it) |
| `test_items(scope)` (Q35) | a scope | Exact, Bounds or NotApplicable | SYS010, SYS011 |
| `effects(u)` (Q34) | a unit | Bounds over the atom registry | section 7 |
| `detectors(lang, atom)` | language and atom | NotApplicable, None or Some(precision) | section 7 |
| `package_of`, `module_path` (Q23) | an artifact | Option | manifest-based inference (2.3 item 6) |
| `scip_occurrences(a)` | an artifact | occurrences with adapter id and version, or Unknown | section 3 (a new query; open question 11.2.9) |

Also needed from neighbours: from gob-directives, the directives of the
`grimble` namespace with their attached unit and span; from gob-lock, the
typed entries and the `renamed` chain (G05). grimble-bind exports the rows
of B, with provenance and status, in the sibling JSON (grimble-model.md 9.5),
for frob to display:

```
{ "entity": "node/gob", "role": "owns", "identity": "crates/gob-walk/src/lib.rs::walk",
  "kind": "function", "status": "must", "source": 2,
  "origin": { "anchor": "node/gob/owns[0]", "specificity": [1,1,-1,-1,0,0] } }
```

and the `hidden` residuals as rows with `"status": "unknown"` and a `reason`
(G03 fixes the schema).

## 9. Worked examples

### 9.1 This repository: crates as nodes, the sibling call as a flow

The model is grmb-spec section 13. Rows of B, with the rank that gave them:

| Entity | Role | Identity | Status | Rank and origin |
|---|---|---|---|---|
| node/gob | owns | `crates/gob-walk/src/lib.rs::walk` | Must | 2, `node/gob/owns[0]` (`crates/gob-*/**`), specificity (1,1,-1,-1,0,0) |
| node/frob | owns | `crates/frob-ledger/src/lib.rs` (its module unit) | Must | 2, `crates/frob-*/**`, (1,1,-1,-1,0,0); `crates/frob/**` has vector (1,2,-1,0,0,0) but does not match this file |
| node/frob | owns | `crates/frob/src/main.rs::main` | Must | 2, `crates/frob/**` |
| flow/f_walk | producer | `crates/gob-walk/src/lib.rs::walk` | Must | 2, `producer` literal path |
| flow/f_walk | consumer | `crates/frob-check/src/snapshot.rs` (module unit) | Must | 2, literal file path |
| contract/walk_result | shape | `crates/gob-walk/src/lib.rs::WalkResult` | Must | 2, literal |
| claim/no_frob_to_grimble | evidence | `crates/frob/tests/wiring.rs` (and its tests) | Must | 2, file selector gives the file and its test units |

Checks over these rows. `f_walk : gob -> frob` has a producer owned by `gob`
and a consumer owned by `frob`: no SYS003 `end-owner`. Had the consumer been
`crates/gob-check/src/lib.rs` (owned by `gob`), `end-owner` would fire naming
the consumer and the owner. No two `owns` selectors match one file, so no
SYS002.

The sibling call. frob invokes the grimble binary and reads
`grimble check --json`. Two different things: the CALL is control (frob
holds `may exec at "crates/frob-check/src/sibling.rs::*"`, a capability), the
RESULT is data. The data flow runs from grimble to frob, so the existing claim
`noflow frob -> grimble` (D28: products do not depend on each other) remains
true, which is why the flow is declared in that direction:

```
flow f_sibling : grimble -> frob {
  label Internal;
  producer "crates/grimble-check/src/sibling.rs::emit";
  consumer "crates/frob-check/src/sibling.rs::read";
  contract sibling_doc;
}
contract sibling_doc {
  shape "crates/grimble-check/src/sibling.rs::SiblingDoc";
  versioning scheme=integer current="1" compat=backward;
}
```

Today the producer and shape paths name files of crates that do not exist:
MDL005 (Warn) for each, SYS004 and SYS009 suppressed, B has no rows for them
(a model describing the future). When G09 creates the file, rows appear:
producer at Must (a literal path), shape Must, consumer Must once
`crates/frob-check/src/sibling.rs` exists. Then `grimble ack flow/f_sibling`
records two flow entries; the Contract facet of `SiblingDoc` (its normalized
fields and types) is `shape_contract` in both. Adding a field to `SiblingDoc`
changes `S_live`: SYS006 fires on both ends ("both behind"), naming the
digests, and `compat=backward` lowers it to Warn for the consumer end only if
the consumer ack is the one behind the producer's. The body of `emit` changing
without the shape changing is SYS007 (Body facet), not SYS006.

### 9.2 A Python service calling a Rust library over FFI

Model (a repository with `svc/` in Python and `crates/scorer/` in Rust):

```
node svc : trusted { owns "svc/**"; }
node scorer : trusted { owns "crates/scorer/**"; }
flow f_score : svc -> scorer {
  label Internal;
  transport ffi;
  contract score_request;
}
contract score_request { shape "crates/scorer/src/lib.rs::ScoreRequest"; }
```

The flow names no `producer` or `consumer` clause. The ends are bound by
explicit directives in the code, rank 1, because the pyo3 module name is a
manifest fact and inference would be May at best:

```python
# svc/app.py
# grimble:binds design:flow/f_score role=producer
# grimble:binds crates/scorer/src/lib.rs::py_score via="manual"
def score(req): return _scorer.py_score(req)
```

```rust
// crates/scorer/src/lib.rs
// grimble:binds design:flow/f_score role=consumer
#[pyfunction] pub fn py_score(req: ScoreRequest) -> f64 { ... }
```

Rows: `(flow/f_score, producer, svc/app.py::score, Must, rank 1)` and
`(flow/f_score, consumer, crates/scorer/src/lib.rs::py_score, Must, rank 1)`;
C: `(svc/app.py::score, crates/scorer/src/lib.rs::py_score, Must, manual, rank 1)`.
Owners: `svc` owns the Python function (rank 2, `svc/**`, Must) and `scorer` the
Rust function: the `end-owner` check passes. Call graph: the call in
`score` to `_scorer.py_score` crosses the C edge, so an undeclared-flow rule
(SYS013) sees one resolved edge from owner `svc` to owner `scorer`, covered by
`f_score`.

If the pyo3 pack is enabled and the flow asks `attr infer = pyo3::pyfunction`,
the rule proposes the same pair at May with `Inference{pack=pyo3, rule=
pyfunction}` in provenance; the rank 1 rows win and the rank 3 rows are
`overridden` provenance. If the rule proposed a DIFFERENT consumer (a different
function of the same module), rank 1 still wins and no finding fires (inference
never conflicts, 2.3 item 5). If the Rust file were later split so that `py_score`
moved, the directive's symref operand would not resolve: SYS003 `dangling-operand`
on the Python side (a symref operand; with SYS008 not applicable because the
directive is not an ack entry). Contract skew works across languages because
SYS006 compares the Contract facet of `ScoreRequest`, a language-neutral
normalization (code-model.md section 2), never the Python or Rust Sig digests.

### 9.3 A notebook: identities per cell, owner May

`analysis.ipynb` (lint-requirements.md 7.4) has cells a1 (markdown), b2 (`def load`),
c3 (`df = load(...)`), d4 and e5 (`!pip install foo`). Identities:
`analysis.ipynb#cell=b2::load`, `analysis.ipynb#cell=c3`, and so on; a markdown
heading is `analysis.ipynb#load-data`. The model:

```
node etl : trusted { owns "analysis.ipynb"; }
node loaders : trusted { owns "analysis.ipynb::load"; }
```

- `etl`: the file selector; every cell unit is contained Must; the cell e5 is
  `Opaque{ShellEscape}`, so e5 contributes a hidden placeholder to `etl`'s
  `owns` (an opaque region may define names). The row for `b2::load` is
  Must (specificity (2,1,0,0,0,0): level 2, a literal file with no `::`).
- `loaders`: the selector `analysis.ipynb::load` has level 3 (symbol). A literal
  selector resolves by the order of code-model.md section 2, unique qualname
  first. In this notebook `load` is defined once, in b2, so a unique
  resolution gives Must. If a cell b7 redefines `load` (legal: a shared
  namespace), there are two candidates and the rows become May for both cells
  with `Inference`-free provenance `Selector{... candidates = 2}`.
- Owner of `b2::load` with the redefinition: candidates `etl` (Must, vector
  (2,1,0,0,0,0)) and `loaders` (May, vector (3,1,0,0,1,0), higher). The
  possible-worlds function (2.2): `loaders` is more specific and may match,
  so `etl` is dominated only if `loaders` is Must; it is not, so
  `owner = Bounds{lo = {}, hi = {etl, loaders}}`: owner May. SYS002 does not
  fire (no Must tie); SYS005 and CAP rules over `b2::load` are Unresolved
  with `may-only-owner`; the fix is a clearer selector (`#cell=b2::load`).
- Acks. With nbformat 4.5 each cell has a stable id, so the identities are
  stable and `grimble ack` can key `analysis.ipynb#cell=b2::load`. With an older
  notebook the cell index is positional: identities are Unstable, refused as a
  lock key, and the ack falls back to a file-level entry (5.5).
- Digests: Body is over the cell `source` only, never outputs or execution
  counts (otherwise every run is drift); the file digest churns on each run
  and is never an ack key.

### 9.4 A Prolog predicate with clauses: a multi-part identity

```prolog
% kb/family.pl
ancestor(A, D) :- parent(A, D).
ancestor(A, D) :- parent(A, X), ancestor(X, D).
```

Both clauses form ONE identity `kb/family.pl::family.ancestor/2` (the name and
arity are the name, so `ancestor/3` would be another identity); the two clause
spans are parts with roles. Model: `node kb : trusted { owns "kb/**";
}` and a flow with `consumer "kb/family.pl::family.ancestor/2"`.

- The consumer row is Must: a literal path to one identity (Q22 resolves the
  multi-part unit as one, not as the ambiguity error between two identities).
- The facets: Sig is `ancestor/2` and its mode declarations; Body is the
  ORDERED composition of both clauses (clause order is semantic in Prolog, so
  reordering changes Body, correctly); Doc is the PlDoc block. Editing either
  clause is a Body change: SYS007 fires for an ack of that identity.
- A dynamic predicate (`seen/1`) has `Body = Absent`: an ack can cover its Sig
  and Attr only, and P0 on Body is NotApplicable for it, not Unresolved.
- Binding through a `call/N`: a rule that reads whether `ancestor/2` is reached
  from the flow's producer gets `hi` = every predicate (the module has
  `Opaque{DynamicDispatch, may_read_scope}`): rank 3 inference and
  reachability are Unresolved, but the ownership row of `ancestor/2` is
  unaffected (ownership is by containment, not by call).
- Rename. A recursive predicate renamed from `ancestor/2` to `forebear/2`
  also edits its own recursive clause, so the Body digests differ and the
  heuristic does not pair them: SYS007 `gone` fires and the human re-acks. A
  non-recursive predicate renamed without touching its clauses has an equal
  Body and is paired at May by SYS008 (when its body is not trivial).

### 9.5 Deny by default and an excuse that cannot hide a use (D75)

Node `frob` (grmb-spec 13) has no grant for `net.listen` and no excuse; the
model says nothing more. A Rust file under `crates/frob/**` calls
`TcpListener::bind`. Cell `(frob, net.listen)`: item 3 of 7.2 finds
`Use_lo` with no covering grant, so the cell is `undeclared` and CAP001
fires. With the file clean the same cell is `denied` (blank) and nothing
fires: deny by default makes the blank cell a decision, and CAP003 is
retired.

Now a model `template gen_proto` excuses `net.listen` for
`lang(rust) & attr(generated_by = "protoc")` (grmb-spec 4.7). Three
cases for a generated file `E(n, a)` covers:

| Observed in the generated file | Cell | Finding |
|---|---|---|
| no use, typed detector complete | `excused` (template and reason shown) | none; the excuse is listed and counted in `check --json` |
| `TcpListener::bind` (Must use) | `uses` | CAP004 Error; CAP001 is not also raised (one root cause) |
| a call the detector reports May, or the file is F1 | `unknown` | CAP004 Unresolved with the reason (`may-use`, `fidelity`, `no-detector`), never a pass |

If the model also granted `may net.listen at "crates/frob/gen/**"`, the
template and the grant overlap: SYS012 fires on the model alone (6.12),
before any code is read.

## 10. Conformance corpus outline for crates/grimble-bind/tests

Location `crates/grimble-bind/tests/corpus/`, run by gob-mdtest (one case per
directory, an `expect` file, D51). A case holds a small repository tree
(code files in several languages, a `.grmb` model, optionally a pack, a
lock and a previous revision) and the expected rows of B with provenance
and the expected findings with reasons.

| Case | What it proves |
|---|---|
| `rank1/entity-operand/` | `design:node/N`, `design:flow/F role=` bind at Must; the sugar spellings give the same rows |
| `rank1/symref-operand/` | resolved Must, ambiguous gives May rows and SYS003 `ambiguous-operand`, unresolved SYS003 `dangling-operand` |
| `rank1/directive-directive/` | two nodes for one identity: Unknown owner, SYS003 `directive-directive` |
| `rank1/directive-selector/` | a directive against a Must selector of another node: SYS003 `directive-selector`, owner stays the directive's |
| `rank1/directive-breaks-tie/` | a directive naming one of two tied nodes resolves the tie, no SYS002, no SYS003 |
| `rank1/directive-vs-may/` | a directive against a May selector: no finding, `overridden` fact |
| `rank1/through-phase/` | a directive attached through a May edge gives a May row |
| `rank2/status-literal/` | literal Must; a glob Must where a literal would be; May under an Unknown attribute |
| `rank2/specificity/` | the total order of grmb-spec 6.5 on the six components, including `src/**` against `src/*/mod.rs` |
| `rank2/tie/` | two Must nodes tied: SYS002, owner Unknown; a May tie: SYS002 Unresolved |
| `rank2/possible-worlds/` | a May more-specific candidate over a Must broader one gives Bounds, not Exact |
| `rank2/hidden/` | an artifact with opaque, hole, phase gives a hidden placeholder; SYS004 never fires; Unresolved `unseen-remainder` |
| `rank2/f0-file/` | file selector owns an F0 file; symbol selector gives only a placeholder |
| `rank2/empty/` | MDL005 versus SYS004 versus MDL010; one root cause one finding |
| `rank3/fill-only/` | inference never adds to a rank 1 or 2 clause; requested by `attr infer` only |
| `rank3/tie/` | ties give no owner and no finding |
| `rank3/overridden/` | rank 3 against rank 1 or 2 is provenance only |
| `rank3/manifest-missing/` | `inference-unavailable`, Unresolved on the rule that needed the row |
| `rank4/foreign/` | `Exact(None)` without a remainder, Unknown with one; SYS001 granularity and directory roll-up |
| `merge/set-roles/` | status max over ranks for a set role; provenance lists every rank |
| `merge/order-independence/` | shuffling file and clause order gives an identical B |
| `merge/singleton/` | `shape`, `runnable`, `ref` with two Must: SYS003 `ambiguous-singleton` |
| `merge/end-owner/` | flow endpoint node versus producer owner: SYS003 `end-owner`, external node exempt |
| `scip/external/` | external index rows are May, never Must |
| `scip/same-adapter/` | same adapter version takes the edge's status; different version is external |
| `scip/stale/` | digest mismatch drops the occurrence with `index-stale` |
| `scip/anonymous/` | anonymous units exported `local`, no rank 3 row |
| `lsp/live-not-admitted/` | a live LSP answer never reaches `check` |
| `mech/b1-b12/` | one case per v1 mechanism of section 4: its v1 input, the source it becomes, the finding id |
| `identity/move-entity/` | an entity moved between files keeps its identity |
| `identity/renamed-from/` | the lock entry migrates, MDL012, no SYS008 |
| `identity/body-rename/` | unique candidate: SYS008 May Advisory; several: all listed; trivial body: SYS007 `gone` |
| `identity/rename-prefix/` | a directory move reported once with the prefix mapping |
| `identity/rename-and-edit/` | a renamed and edited body is not paired and is SYS007 `gone`; after `--rename` an edited body is SYS007 `facet` |
| `identity/unstable/` | positional identity refused as a lock key; file-level fallback |
| `ack/refuse-may/` | an ack of a May row or an Unknown facet is refused with the rows |
| `rules/sys001/` ... `rules/sys012/` | per rule: a firing case, a clean case and each Unresolved condition of section 6, with reason codes |
| `rules/sys005-vacuous/` | modeled selector over an all-F1 language: required Unresolved `vacuous` |
| `rules/sys006-matrix/` | the truth table of `S_p`, `S_c`, `S_live` (equal, one behind, both behind), Unknown on each side |
| `rules/sys007-kinds/` | `facet`, `gone`, `scheme`; F0 and F1 Unresolved |
| `rules/sys012-hierarchy/` | a template excuse for `fs` against a grant `may fs.read` with overlapping selection; disjoint selections are clean; unknown atom is MDL016, not SYS012 (G14) |
| `rules/cap004/` | an excused atom observed in covered code: CAP004, no CAP001; a May or Unknown use, a missing detector and an F1 file give Unresolved, never a pass; a grant covering the same use still gives CAP004 |
| `matrix/cells/` | each cell (uses, undeclared, declared-unused, denied, excused, not-applicable, unknown), the May-owner effects (7.2), the `no-code` row |
| `matrix/not-applicable/` | detector-declared NotApplicable versus a template excuse; a node-level `excuses` is MDL018 |
| `example/deny-default/` | 9.5: the three template cases and the CAP001 case |
| `matrix/excuse-order/` | 7.2 order: an observed use in excused code is evaluated before the excuse, so the cell is never `excused` over a use |
| `matrix/aggregate/` | Rust plus Python plus CSS node: the per-language breakdown and the one Unresolved per node |
| `example/frob-repo/` | the model of grmb-spec 13 over a small copy of this repository: expected rows of 9.1 |
| `example/ffi/` | 9.2 |
| `example/notebook/` | 9.3, both nbformat versions |
| `example/prolog/` | 9.4 |

## 11. Open questions

### 11.1 Answers proposed to grmb-spec.md's open questions

3. Selector text across crates (slice the text from the .grmb token stream and
   re-parse in gob-walk, or a token-level parser). PROPOSED: slice and
   re-parse is acceptable, under two conditions. (i) `Selector::parse` takes
   the base span of the text, returns spans already mapped into the .grmb file
   (and through the escape table of a string literal), so a finding can point at the
   clause and at a glob within it. (ii) B stores only the clause anchor and the
   glob index of the matching branch, never a token index, so provenance stays
   valid when the clause is reformatted. gob-walk then needs no knowledge of
   `.grmb` tokens. Binding semantics needs nothing finer than the clause range.
4. Kernel verdict and V-model closure rule ids. Binding decides two of them
   and proposes the rest. Decided: no-evidence is SYS010; unresolved vmodel
   links are SYS011 (here). PROPOSED for G16: V-model closure rules
   VMOD001 (orphan requirement), VMOD002 (unjustified design), VMOD003
   (untested artifact), VMOD004 (orphan test), VMOD005 (trace cycle); claim
   verdicts CLAIM001 (REFUTED, Error with the witness), CLAIM002 (an
   `assumed` claim past its review date, Error as in v1), and UNPROVABLE with
   no id of its own when the cause is a missing binding (it is SYS010) so
   one root cause is one finding.
6. Directive-form exceptions in .grmb. PROPOSED: yes, allow
   `[[grimble.exception]]` records in `exceptions.toml` with `target =
   "design:node/cli"` (the logical-location form, resolved through the rename
   chain of 5.5), so a tool-written exception (`frob accept`) never edits a
   `.grmb` file. The clause form stays for hand-written exceptions; the rule
   becomes "one spelling per exception", not "one spelling per file kind". The
   `design:` target costs nothing new (the code-side form already exists) and
   it removes the only place where frob would have to rewrite a model.
9. Claim verbs (`frob:effects` and the rest) on `.grmb` units. PROPOSED:
   MDL013 for the eight claim verbs, keep `frob:doc`, `frob:ticket`, `frob:todo`,
   `frob:invariant`, `frob:decision`, `frob:deprecated` and `frob:until`. A claim
   about a model entity ("this node has no effects") is already expressible as
   the absence of grants plus the detector matrix (section 7), which is measured
   rather than asserted; an accepted verb that never fires is an invisible
   variable (D22) and a reviewer cannot tell it from a working check.
12. `renamed_from` versus a generated ULID. PROPOSED: no ULID. A code identity
    has nowhere to carry one, so the body-facet heuristic (5.4) and the explicit
    `grimble ack --rename` are needed anyway; adding ULIDs only for entities
    would add noise to every model file and create a second identity scheme.
    The failure it prevents (an entity renamed and its body edited in one commit
    without `renamed_from`) costs a re-ack of a handful of entries, reported
    as SYS007 `gone` with the unpaired candidate listed, which is cheap and
    visible.

### 11.2 Raised by this design

1. SYS012 (RESOLVED by D75, 2026-10-04). The ticket title "excuse without
   matching grant" was ambiguous. The owner removed node-level excuses
   (they exist only in matrix-build templates) and redefined SYS012 as the
   check that a template excuse does not contradict a grant in the model
   (6.12), implemented in G14. The alternative reading, an excuse that no
   detector or grant could involve, is not a rule. The same decision made
   a blank cell mean "denied" (deny by default), retired CAP003 and added
   CAP004 (excused but used, 7.2 item 3).
2. Rule ids. SYS001-SYS012 as the ticket gives them renumber grimble-model.md
   section 4 and grmb-spec (11.3); undeclared-flow and surface need ids
   (reserved SYS013 and SYS014 here). Is renumbering acceptable before any
   crate exists (it is, nothing consumes the old ids), or should the old ids
   keep their numbers and the ticket's list get new ones?
3. Lock schema. G05 must carry: an entity-kind entry, flow entries with
   `end_contract` and `shape_contract`, and the `renamed` chain. Is `end_contract`
   needed in addition to the facet digests of the end symbol (it is the
   Contract facet, which is a fifth facet in the same scheme)?
4. A code-side rename marker. Entities have `renamed_from`; code identities
   have only the heuristic and `ack --rename`. A `grimble:renamed_from SYMREF`
   directive on the new unit would make a code rename deterministic (Must) at
   the price of a verb and a comment to remove later. Wanted?
5. The inference trigger (`attr infer`). Making inference explicit keeps D22 but
   adds a line per entity. A pack could instead declare default-on rules for
   a node kind; that makes inference ambient and is refused here. Revisit if
   adoption cost shows up in the migration design (M10).
6. The `design:` operand scheme for `grimble:binds` and exceptions needs a row
   in the directive registry of code-model.md section 4 and a typed validator
   (resolved in grimble-bind, since only grimble knows entities).
7. May-owner policy for the matrix. A May owner currently makes cells Unresolved
   and never fires; an adopter with many macros may want a configurable
   "treat May owners as owners" mode for CAP002 shrinking. It breaks the
   honesty contract, so it is refused here.
8. SYS001 granularity. One finding per artifact with a directory roll-up is
   proposed; if the report should instead list directories only, the rule's
   subject becomes a directory.
9. `scip_occurrences` is a new gob-ir query; is the exported same-adapter
   SCIP in scope for the first gob-ir ticket or later?
10. `rename_min_tokens` (12) and `rename_min_group` (5) are guesses; they should
    be tuned on this repository's own history before G12 lands.
11. Severity defaults of the table in section 6 (SYS007 Error, SYS001 and SYS005
    Warn then Error under strict) are proposals for the owner.
12. One root cause, one finding between SYS010 and the kernel's UNPROVABLE
    verdict: is the verdict suppressed when SYS010 fires, or does the status
    output show both with the finding as the cause?
13. Call versus data flow. 9.1 declares the sibling flow grimble to frob (the data)
    and the call as a capability; should the model have a `call` edge distinct
    from `flow`, so `noflow` and call permissions can be stated about calls
    without conflating them with data?

### 11.3 Disagreements with other documents and renumbered ids

This file's ids and rules win. The edits that accompany it:

1. grimble-model.md 9.1 now points here instead of repeating the sources. The
   drift table of its section 4 is superseded by section 6 here (ids and
   conditions); a sentence under that table says so.
2. Id mapping, old to new (grimble-model.md section 4 and grmb-spec):

| Old id (alias) | Old meaning | New id | Notes |
|---|---|---|---|
| SYS001 SYS-EMPTY-SELECTOR | selector matches zero symbols | SYS004 | per binding clause |
| SYS002 SYS-AMBIGUOUS | two equally specific selectors | SYS002 | unchanged id, now Must ties only |
| SYS003 SYS-UNMODELED | public or effectful symbol with no node | SYS005 | opt-in by `modeled` |
| SYS004 SYS-UNDECLARED-FLOW | edge between owners with no flow | SYS013 | reserved, not in the ticket's twelve |
| SYS005 SYS-UNIMPLEMENTED-FLOW | flow, empty producer or consumer | SYS004 (both ends) or SYS009 (one end) | |
| SYS006 SYS-CONTRACT-SKEW | contract facet digests differ | SYS006 | now defined over three digests (6.6) |
| SYS007 SYS-CHANGED | body digest changed since ack | SYS007 | adds kinds `gone`, `scheme` |
| SYS008 SYS-RENAMED | vanished, same-digest appears | SYS008 | Advisory, May pairing |
| SYS009 SYS-SURFACE | public symbol outside `surface` | SYS014 | reserved |
| (none) | FOREIGN, decided in grimble-model.md section 8 | SYS001 | new |
| (none) | conflicting bindings; `SYS-CONTRACT-AMBIGUOUS` | SYS003 | new |
| (none) | claims without evidence, vmodel links, template excuse versus grant | SYS010, SYS011, SYS012 | new (SYS012 redefined by D75 as a matrix-build check, G14) |

3. grmb-spec.md: the references to SYS001, SYS002, SYS005 and SYS009 in its
   text (MDL005, 4.1, 4.2, 4.3, 6.4, 6.5, 10.3, 13 and 14.1) follow the table
   above; a pointer sentence under 10.3 records that this file refines its
   conflict rules. The two refinements: (i) rank 1 against a different Must
   at rank 2 is the finding SYS003 `directive-selector` (grmb-spec 10.3 rule 1
   kept it an advisory fact; a mismatch between a code attestation and the model
   is the case the v1 proposal said must be a finding); (ii) within rank 1, two
   different nodes on one identity are SYS003, not SYS002 (a contradiction is
   not a tie that more specific text can break). The owner function gains the
   possible-worlds reading of 2.2.
4. SYS013 (undeclared flow, the old SYS004) and SYS014 (surface, the old SYS009)
   keep their conditions from grimble-model.md section 4 and are assigned to the
   grimble-bind second ticket (G12); they are rules over B and edges (B6, B5 of
   section 4) and are not specified further here.
5. code-model.md section 6 describes `binds` as an inference; this file adds
   that the explicit `via="manual"` form is rank 1 of the relation C (1.4), the
   same source ordering as for B.
