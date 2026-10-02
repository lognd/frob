# grimble end-to-end review (design goblin vs the universal structural model U)

Status: audit findings only, 2026-10-02, branch `experimental` at f18c201bb.
Nothing was run (no cargo, no frob); every claim about code is by reading.
Scope: is grimble (the `.grmb` model language, binding, drift, capability
matrix, structural lints, standalone binary orchestrated by frob) thought
out end to end now that docs/design/universal-model.md (DRAFT, "U") exists?

Counts: 4 HIGH, 12 MEDIUM, 7 LOW. The milestone-2 ticket cut is section 5,
the list of things grimble needs from U that U does not provide is section 4.

Short answers to the nine questions (details in the findings):

| Q | Answer | Findings |
|---|---|---|
| 1 Model language | Not fully specified: no lexical rules, no EBNF, no binder/scoping rules, no versioning, cross-module story dropped; no U adapter for `.grmb`; no formal binding relation | H1, M1, M2 |
| 2 Binding | v1 B1-B12 map onto U queries only partly; three mechanisms have no v2 home; the call graph's May status makes the flagship SYS004 unable to fire on calls; "inferred, symref canonical, SCIP derived" is coherent only with an identity notion U contradicts | H1, M4, M5, M12, L2 |
| 3 Drift findings | Digests are whitespace-collapsed text, not U facets; SYS006 is unrepresentable in gob-lock; ack mechanics are not in gob-lock; F0/F1 behaviour unstated; kernel and attestation findings have no ids | H2, M3, M7 |
| 4 Capability matrix | `n/a` is defined three incompatible ways; no detector-kind column; packs contradict the closed atom set | H4 |
| 5 Rules | Level-2 universal rule syntax targets the superseded IrKind; callee vocabulary has no owner; grimble-check would duplicate frob-check | M6, M8 |
| 6 Boundaries | The sibling `--json` contract is a name, not a schema; Unresolved sorts below Advisory so an absent grimble never fails a gate; `--only SYS` errors without `bundle`; cache and budget for the sibling run unstated | H3, M6, M11 |
| 7 Packs, drift-lock | Under-specified; the drift-lock needs ticket state (violates D28); pack enablement and pack versions are invisible variables | M9 |
| 8 Adoption | No `grimble init` spec, no stated model-free default, verbs missing owners or missing entirely (doctor, exceptions, fmt), no `.grmb` printer for shrink/migrate | M10 |
| 9 Milestone 2 | Proposed in section 5: 4 design tickets, then 15 implementation tickets | - |

---

## 1. HIGH

### H1. No formal relation between a `.grmb` model and the U term it describes; `.grmb` has no U adapter; identity is contradictory (HIGH)

- Where: docs/design/grimble-model.md section 4 lines 100-115 (binding table:
  "Resolves to set of symbols"), section 8 lines 195-198 (".grmb is its own
  language with its own parser"); docs/design/universal-model.md section 2.2
  lines 75-79 (identity = "content hash of its alpha-normal form by default";
  "Symrefs are names FOR identities"), section 3.1 lines 160-173 (adapter
  tuple), section 6 line 389 (".grmb" listed under markup and documents at
  fidelity F4); docs/design/code-model.md section 3 line 98
  (`grimble-model` "its own parser, no tree-sitter"); README D22 (".grmb is
  its own language").
- What: three gaps that together mean "binds" has no definition.
  1. Binding is described only operationally ("resolves to set of symbols").
     There is no statement of the relation. Under U it should be a relation
     `Bind subset-of Entity x Identity x {Must, May, Unknown}` computed as
     `owns(n) = select(selectors(n))` (lint-requirements Q32, which already
     returns `Bounds<Set<Sym>>`) with `owner(u)` = most specific selector,
     and every SYS/CAP rule stated with a polarity over the lo/hi of that
     relation. None of this is written; R28/R29 in
     notes/research/lint-requirements.md lines 115-116 give polarities for
     only SYS001, SYS003, SYS009, CAP001-003.
  2. `.grmb` has no adapter A_grmb = (parse, rho, bind, cap). U's table
     claims F4 for it (universal-model.md line 389) but nobody owns T_grmb:
     gob-languages cannot depend on grimble-model (boundaries.md section 6
     line 291), and grimble-model is specified with no U output. Consequence:
     frob sees every `.grmb` file as an opaque F0 artifact (or, today, as an
     empty file, gap G19), so `frob:doc`/`frob:ticket` directives above
     model constructs (188 and 90 of them in the v1 self-model, B4 in
     notes/v1/strata.md line 317) cannot bind. code-model.md line 17 still
     promises "the directive DSL in ... .grmb files".
  3. U says identity is a content hash of the alpha-normal form. A body
     edit therefore yields a new identity, yet SYS007 SYS-CHANGED is "bound
     symbol's body digest changed" (grimble-model.md line 134) and SYS008
     SYS-RENAMED is "vanished, same-digest symbol appeared elsewhere" (line
     135): both presuppose an identity that survives body edits and a
     second notion (digest) that does not. gob-lock keys entries by symref
     string (crates/gob-lock/src/file.rs lines 104-112), a third notion.
- Why it matters: every grimble rule is a predicate over this relation.
  Without it the honesty theorem (universal-model.md section 4.5) cannot be
  applied to grimble, two implementers will disagree on what a selector
  matching a macro-generated symbol means, and frob loses the v1 B4 binding
  of tickets and docs to design constructs.
- Failure scenario: `node api { owns "src/api/**"; }` over a Rust file whose
  handlers are generated by a proc macro (`phase` with no expansion,
  universal-model.md line 112). select() returns Bounds{lo: hand-written
  fns, hi: unknown}. Nothing says whether SYS001 (zero match) is clean,
  whether SYS003 UNMODELED treats the hidden symbols as claimed, or whether
  the next `grimble ack` keys the handlers by symref (unstable under rename)
  or by content (unstable under any edit).
- Suggested resolution: add a section "Binding semantics over U" to
  grimble-model.md that (a) defines the relation above with status, (b)
  defines identity for grimble as `(symref, unit kind)` with digests as
  facets, and states that U section 2.2's content hash is the
  rename-detection key (by_digest, Q42), not the identity (fix U 2.2 to say
  "identity = adapter-stable id, default symref; content hash is a facet");
  (c) gives every SYS and CAP id a polarity row (section 4 of this file
  lists them); (d) specifies A_grmb: grimble-model emits a U term (units =
  node, store, flow, boundary, claim, vmodel; scope graph = entity names
  declared at module scope, Must references from flows and boundaries;
  comments bound to constructs) at F4, and since frob may not link
  grimble, `grimble graph --json` exports that term (entities, spans,
  facet digests) so frob can bind `frob:` directives in `.grmb` through the
  sibling JSON (D28 compatible). Record the decision as a D-row.

### H2. Drift digests are not defined over U facets; gob-lock cannot represent SYS006; nothing says who computes digests standalone or what F0/F1 languages yield (HIGH)

- Where: grimble-model.md lines 133-135 (SYS006 "contract symbol
  fingerprint differs between the producer and consumer acks"; SYS007 body
  digest; SYS008 same digest); code-model.md lines 60-79 (whitespace-
  collapsed text digests; `Sig` lattice "never used for digests");
  crates/gob-symbols/src/model.rs lines 91-116 (`Digests{sig, body, doc}`,
  `collapse_ws`); crates/gob-lock/src/file.rs lines 61-79 (`LockEntry`:
  sig, body, doc, targets), lines 104-112 (one entry per symref string);
  universal-model.md lines 444-453 (G7, G8, G9 "must be settled before any
  consumer repository commits a frob.lock"), lines 191-208 (fidelity: F0
  gives only whole-artifact digests).
- What:
  1. SYS006 as written is unrepresentable. A contract symbol has one lock
     entry keyed by its symref; there is no "producer ack" and "consumer
     ack" of the same contract, no role, no flow key. For a cross-language
     flow the producer side and consumer side are different symbols in
     different languages, so the comparison must be over `norm_sig`
     (Q39, the Type lattice), which code-model.md line 78 explicitly
     excludes from digests.
  2. The digests grimble.lock would store are the landed whitespace-
     collapsed text digests, which U already marks wrong (G7 attributes
     outside sig, so `#[pyfunction]` changes are invisible; G8 comments in
     bodies change the body digest; whitespace collapse is wrong for
     indentation languages). `LOCK_VERSION` (file.rs line 9) versions the
     file format, not the digest scheme, so a digest-scheme change silently
     invalidates every ack.
  3. Standalone grimble must compute digests itself; it can through
     gob-symbols, but nothing says so, and the per-language digest is only
     defined for Rust and markdown.
  4. F0/F1 languages have no per-symbol facets (U section 3.3). The design
     never says that SYS006/SYS007/SYS008 are P0 rules and therefore
     Unresolved (not clean, not firing) on F0/F1, nor how that rolls up.
- Why it matters: SYS006 and SYS007 are the cross-language contract checks
  audit H7 called "the checks that justify grimble's existence"; D28 moved
  their storage to gob-lock without making the store able to hold them.
  Committing the first grimble.lock before G7-G9 are fixed bakes in digests
  that will all drift at once.
- Failure scenario: flow `f_score : web -> kernel` with producer
  `web/client.ts::score`, consumer `crates/kernel/src/lib.rs::score`,
  contract `crates/kernel/src/lib.rs::ScoreRequest`. The Rust struct gains a
  field. `grimble ack` on the consumer side records the new body digest
  under `crates/kernel/src/lib.rs::ScoreRequest`; there is no second entry
  for the producer's view, so SYS006 can never fire, and the TS client
  keeps sending the old shape with a green check.
- Suggested resolution: (a) define a grimble lock entry kind for flows:
  key `flow:<id>`, fields `{contract_sig_norm, producer_sig_norm,
  consumer_sig_norm, acked_by, acked_at, reason}` where `*_sig_norm` is the
  digest of the canonical `norm_sig` stream; SYS006 = "current
  contract_sig_norm differs from the value acked at either endpoint"
  (P0, Exact only). Extend gob-lock with typed entry kinds (symbol, flow)
  and a `digest_scheme` field separate from `version`. (b) Make all grimble
  digests the U canonical facet stream (Sig, Body, Doc, Attr) and block the
  first grimble.lock on G7-G9 (ticket G05 in section 5). (c) State in
  grimble-model.md section 4: digests are computed in-process via
  gob-symbols/gob-ir by grimble itself; SYS006-008 are P0; on a unit whose
  adapter is below F2 for the facet, the finding is Unresolved, rolled up
  once per (rule, language, node).

### H3. The sibling `--json` contract is unspecified, and Unresolved sorts below Advisory so an absent or unmeasuring grimble never fails a gate (HIGH)

- Where: boundaries.md lines 29-35, 189-199, 245-253, 294-301; products.md
  lines 106-111; cli.md lines 32-53 (generic envelope, one global
  `schema_version: 1`); crates/gob-diagnostics/src/record.rs lines 10-31
  (`FindingRecord`: rule, slug, severity, file, line, column, message,
  fingerprint, fix title; `Serialize` only); crates/gob-diagnostics/src/
  envelope.rs line 9 (`SCHEMA_VERSION = 1`); crates/gob-rules/src/meta.rs
  lines 7-18 (`Severity` ordered `Unresolved < Advisory < Warn < Error`);
  rules.md lines 25-28 and 200-202 (`--fail-on` by severity).
- What: D28 makes the JSON the only channel between frob and grimble, and
  frob must (a) merge findings, (b) evaluate ticket-bound exits of grimble
  exceptions, (c) enforce the close guard, (d) validate `implements
  design:node/x`, (e) traverse `binds` edges for AFFECT and evidence reach,
  (f) render the capability census. The landed record carries none of:
  product namespace, byte range (frob re-renders spans), the exception that
  suppressed a finding (kind, opaque ticket, exit status), the suppressed
  list itself, the Unresolved reason and rollup key, the per-language
  fidelity/coverage report, entity and `binds` lists, or a per-verb data
  schema version distinct from the envelope version. FindingRecord is
  Serialize-only, so frob has no type to parse it back. And because
  Unresolved is the lowest severity, `[check] fail_on = "error"` (the
  default, D39) passes when grimble is configured but missing, when its
  schema mismatches, and when a node's whole language is unmeasured.
- Why it matters: the "unmeasured is not zero" principle is visible in the
  report but has no teeth at the gate; the one command agents run gives a
  green land with zero grimble evaluation. Without a schema, frob's
  EXC003/EXC007 over grimble defers (exceptions.md lines 33-41) cannot be
  built.
- Failure scenario: a repo has grimble.toml; the CI image installs crates.io
  `frob-cli` (no `bundle`) and not grimble. `frob check --fail-on error`
  emits one Unresolved "grimble configured but not installed" and exits 0;
  `frob land` lands a change adding an undeclared `net.connect` that
  CAP001 (Error) would have refused.
- Suggested resolution: write `docs/design/grimble-json.md` (or a section
  in boundaries.md) defining `grimble check --json` data: `schema:
  "grimble.check/1"`, `findings[]` = FindingRecord plus `product`,
  `range{start,end}`, `entity` (logical location, e.g. `node/cli`),
  `polarity`, `unresolved{reason, rollup}`; `excepted[]` = finding plus
  `exception{kind, site, because, ticket (opaque), exit: Evaluated(state) |
  UnresolvedExit}`; `fidelity[]` per language (level, capability cells);
  `subjects` per rule; `entities[]` and `binds[]` (or put those in `grimble
  graph --json`). Derive `Deserialize` and `JsonSchema` on the record in
  gob-diagnostics so frob parses with the same type. Add a gate knob
  `[check] fail_on_unresolved = ["sibling-missing", "schema-mismatch"]`
  (materialized, default both) or make sibling-missing a GuardNeedsAction
  refusal (exit 3) in `land`, so absence cannot pass silently.

### H4. The capability matrix's `n/a` is defined three incompatible ways, there is no detector declaration (no detector-kind column), and packs contradict the closed atom set (HIGH)

- Where: code-model.md line 284 (`n/a`: "adapter matrix says
  NotApplicable; reported as one Unresolved per node"); universal-model.md
  lines 219-222 (`NotApplicable` "distinct from Unknown so rules can skip
  rather than nag") and lines 483-484 ("an `n/a` cell is a declared Unknown
  and is reported as Unresolved"); notes/research/lint-requirements.md
  lines 152-155 (NotApplicable rolled up "per (rule, language, scope)");
  notes/research/paradigms.md lines 1166-1179 (DETECTOR KIND column;
  `unknown-by-design` distinct from `n/a`); grimble-model.md lines 141-147
  (detectors "held in a data registry with v1's row schema"), lines 163-165
  ("A pack contributes capability atoms, detectors"); code-model.md lines
  262-275 (atoms are "a closed, extensible set ... declared in Rust" via
  `#[derive(Capability)]`); universal-model.md line 286 (`effects(region)`
  is a U capability in gob-ir).
- What: the same cell has three meanings. Under U's lattice, "the language
  cannot have this effect" (CSS cannot `exec`) is NotApplicable (skip,
  clean), "the adapter has no detector" is Unknown (Unresolved), and
  "undecidable without execution" (Bash `$cmd`, `eval`) is Unknown by
  design. The matrix collapses them into `n/a` and universal-model section
  8 relabels all of them Unknown, which makes a CSS-only node nag forever,
  while an implementer following U 4.1 literally would map "no detector" to
  NotApplicable and skip, which is the silent pass M16 fixed. There is also
  no mechanism by which an adapter declares, per atom, whether it detects
  it, how (import path, command name, resource type, signature marker,
  host-interface list, permission block, value flow), and at what
  precision; U's adapter tuple has `cap_L` but no query exposes it to
  rules, so CAP003 "applicable to the node's languages" has nothing to read.
  Finally, atoms are a closed Rust enum (derive) but packs "contribute
  capability atoms" as TOML, and `effects` lives in gob-ir which may not
  depend on grimble-capabilities where the atoms are declared.
- Why it matters: the capability matrix is v1's most-used feature
  (notes/v1/strata.md line 807); its honesty is the reason grimble exists.
- Failure scenario: a node owns `scripts/**/*.sh` and `src/**/*.rs`. At
  milestone 2 only Rust has detectors. The summary shows Rust cells as
  uses/undeclared and Bash cells as `n/a`. If `n/a` is NotApplicable, the
  node reads clean although `scripts/deploy.sh` runs `curl | sh`; if it is
  Unknown, a pure-CSS node owning `web/**/*.css` carries a permanent
  Unresolved for `exec`, `net.connect`, `fs.write`.
- Suggested resolution: make the cell set `uses | undeclared |
  declared-unused | excused(reason) | not-applicable(reason) |
  unmeasured(language) | unknown-by-design(reason)`; `not-applicable` comes
  from the adapter declaring the atom impossible for the language (clean),
  `unmeasured` and `unknown-by-design` are Unresolved rolled up once per
  (node, language). Put the atom table in substrate (gob-ir: `AtomId` and
  the atom registry as data) so `effects` can return atoms, keep the
  `Capability` derive for documentation and ids; let packs add atoms only
  through the same registry with a pack-qualified id (`pii.collect`). Add a
  detector registry row schema: `{atom, language, detector_kind,
  pattern_or_vocab_ref, precision: Typed|Lexical, cwe, rationale,
  safer_alternative, severity}` and expose `detectors(lang, atom) ->
  NotApplicable | None | Some(precision)` as a U capability query. Fix the
  three documents to one wording.

---

## 2. MEDIUM

### M1. `.grmb` grammar is an example, not a specification (MEDIUM)

- Where: grimble-model.md lines 23-89; notes/v1/strata.md lines 50-54 (v1
  lexical rules), 63 (v1 import/export, parse-only).
- What: missing: (a) lexical rules (identifier charset, string escapes,
  comment syntax, reserved words, number-with-unit tokens and the unit
  table; "Units are types as in v1" points at a Python unit system); (b) an
  EBNF; (c) binders and scope of entity names (module-global? may a
  fragment shadow? are flow ids in the same namespace as node ids?); (d)
  `part of` semantics now that fragments "can declare anything" (duplicate
  ids across fragments, merge order, what `extend` became); (e) cross-module
  references (import/export was dropped, but a monorepo with two `module`
  roots needs a rule: forbidden, or qualified names); (f) a language version
  header or edition, needed once packs and grammar evolve; (g) the selector
  and atom sub-grammars: `owns "path::qual"` is a string but `surface pub
  fn *, "Cli"` mixes unquoted kind filters with strings; `may
  net.connect:api.github.com` puts an argument inside the atom token; `of
  CONSTRAINT` and the "optional kind filter" have no syntax; (h) trust and
  label lattice declarations (v1 lattices were "user-extensible", line 181
  of the strata note; v2 never says how). The example itself is ill-formed
  under any reasonable scoping: `symbols`, `registry`, `vet` and flow
  `f_install` are referenced but never declared (lines 41, 48, 50).
- Why it matters: D22 requires the editor grammar to be generated from the
  keyword table and the parser to be a leaf crate; neither can be written
  from an example.
- Failure scenario: two fragments both declare `node cli`; one implementer
  merges, another errors; the generated editor grammar accepts `surface pub
  fn *` while the parser rejects it.
- Suggested resolution: add grimble-model.md section 2a "Lexical and
  syntactic specification" with an EBNF, a scoping section (one namespace
  per module for entity ids; duplicate id = model-load error; references
  resolve Must within the module), `grimble 1` as a required first line,
  the unit table, and selector/atom grammar shared with gob-walk (M12). Fix
  the example.

### M2. `.grmb` exceptions disagree with the shared exception grammar, and their matching, attestation and knobs are undefined (MEDIUM)

- Where: grimble-model.md lines 57-58 and 79-82 (`accept SYS004 on cli
  because "..."`; `defer ... ticket ID reason "..."`); exceptions.md lines
  61-62 ("All four exception verbs spell the reason `because=`"), lines
  64-74 (`[[frob.attest]]` only), table lines 146-151 (EXC005 = REATTEST
  against `frob.lock`, frob-obligations); boundaries.md lines 138-139
  (EXC005 and EXC007 listed as frob's ticket-bound exits); rules.md lines
  285-287 (ticket-bound exits "EXC003 EXC007"); rules.md section 5 lines
  229-231 (matching modes: symbol-exact, file, package); architecture.md
  lines 240-245 (`[exceptions]` knobs only in frob.toml);
  crates/gob-directives/src/frob.rs lines 90-106 (`Defer.ticket` is a
  `ticket_ref`, validated as a full ULID).
- What: the `.grmb` form uses `reason` for defer and an unkeyed `because`;
  exceptions `on NODE` need a matching mode "every finding whose subject is
  owned by NODE or anchored at the node's span" that rules.md does not
  have; REATTEST for an accept on a node has no digest to compare (a node
  has no body facet unless H1's A_grmb defines one); the only attestation
  store named is `[[frob.attest]]`; the REATTEST rule id (EXC005) is owned by
  frob-obligations in exceptions.md and also listed as a ticket-bound exit
  in boundaries.md while rules.md names EXC003, so standalone grimble has
  no rule it may emit for REATTEST; hotfix expiry and reason policy are
  date- and text-based (evaluable standalone) but their knobs live only in
  frob.toml, which grimble may not read. The shared `Defer` derive validates
  ULID shape, which is ticket knowledge the "opaque" rule says grimble lacks
  (harmless if grimble declares its own derive, but unstated).
- Why it matters: exceptions are how grimble findings become adoptable; a
  grimble-only repo cannot configure or attest them.
- Failure scenario: `accept CAP001 on cli because "CLI downloads releases"`
  in `design/frob.grmb`; the node later gains a second downloader. No
  digest exists, no REATTEST fires, the accept silently covers new code.
- Suggested resolution: one grammar (`because`), node-scoped matching
  defined as "finding subject owned by the node", attestation of a node =
  digest of the node's owned-symbol set plus its declaration
  (`[[grimble.attest]]`), renumber so REATTEST is a gob-rules id emitted
  under the excepted product, move `[exceptions]` non-ticket knobs into a
  shared table each product reads from its own config file, and state that
  grimble's exception directives take `ticket` as an opaque string.

### M3. Several grimble outputs have no rule id: kernel verdicts, V-model closure, model-load errors, attestations, FOREIGN (MEDIUM)

- Where: grimble-model.md lines 91-98 (kernel computes claim verdicts
  PROVED/REFUTED, V-model closure, assume expiry), lines 115 (attestations
  `grimble:node/channel/boundary/effect` "checked against the model"),
  lines 123-136 (the only ids: SYS001-009, CAP001-003), lines 195-198
  ("FOREIGN symbols are Warn until strict"); rules.md line 268; boundaries.md
  2.5 lines 142-147 (grimble families: SYS, BIND, CAP, CYCLE, ARCH, LARGE,
  DEAD, DUP, SEC, PII, VET, GPOL); notes/v1/strata.md lines 476-479 (v1
  SYS001 dangling directive, SYS004 parse failure), 553-555 (claims, VMOD001,
  MSCLOSE001); audit-resolution M16 (SYS003 made opt-in to avoid flooding).
- What: a REFUTED `assert noflow`, an overdue `assume`, a V-model orphan
  requirement, a `.grmb` semantic error (unknown node in a flow, duplicate
  id, unknown atom, unit mismatch), a `grimble:channel` naming an unknown
  flow, a `grimble:node` override that contradicts `owns`, and a
  `grimble:effect` for an ungranted atom all have no family or id. FOREIGN
  is described as a Warn finding with no id, re-introducing the repo-wide
  flood M16 removed by making SYS003 opt-in. v1 SYS004 (parse failure) and
  v2 SYS004 (undeclared flow) share a number with different meanings, and
  v1 SYS001/SYS003 likewise change meaning, so an unmigrated
  `frob:waive SYS003` silently becomes an exception of a different rule.
- Why it matters: unowned outputs are not built or cannot be excepted,
  ratcheted, or counted; the kernel crate has no consumer.
- Failure scenario: a user writes `assert noflow foreign -> ledger`; a new
  flow makes it REFUTED; `grimble check` has no rule to report it, or
  reports it under an ad hoc id that exceptions cannot name.
- Suggested resolution: add families: `CLAIM` (REFUTED, UNPROVABLE,
  assume overdue) and `VMOD` (the five closure rules plus milestone gaps)
  in grimble-kernel; model-load semantic errors as `GRMB` (or PARSE002+
  under the grimble namespace); attestation drift as SYS010-SYS012; make
  FOREIGN either an alias of SYS003 under `[grimble] modeled` or Advisory
  until `strict`. Publish the v1-to-v2 SYS map and make `grimble migrate`
  refuse to carry a waiver whose id changed meaning without rewriting it.

### M4. Under U's polarity rules the flagship checks cannot fire on Rust calls, and shrink cannot certify (MEDIUM)

- Where: universal-model.md lines 233-238 (P+ fires on `lo`), lines
  474-476 (gob-symbols' call graph "becomes `apply_targets` at precision
  'by name within project, May'"); grimble-model.md lines 128-131 (CAP001
  Error, CAP002 shrink-only, SYS004 import or call edge);
  crates/gob-symbols/src/graph.rs lines 37-60 (`CallEdge::Resolved` means a
  unique name in the crate, gap G2); lint-requirements.md line 104 (R17 is
  P+), line 116 (CAP002 is P-: fire iff hi lacks).
- What: if every Rust call edge is May, SYS004 over calls (P+) and CAP001
  over effect sites reached through calls can only ever be Unresolved,
  never fire. Conversely CAP002 "grant never observed" is P- and needs
  `hi` to lack the atom; any opaque region in scope (every `println!`,
  `format!`, `tracing::info!` is a macro `phase` without expansion) puts a
  wildcard in `hi`, so CAP002 and `grimble shrink` almost never certify on
  Rust. The design does not say which precision the Rust adapter must reach
  for grimble to be useful, nor that SYS004 at milestone 2 is effectively
  import-only.
- Why it matters: without a stated precision target, grimble ships a
  matrix full of Unresolved and the user sees no value; or an implementer
  "fixes" it by treating May as Must and breaks Theorem 3.
- Failure scenario: `crates/frob-check` calls `gob_exec::Runner::spawn`;
  the edge is May (name-only), so the undeclared flow `check -> exec` and
  the observed `exec` atom are Unresolved; `grimble shrink` refuses to
  remove an unused `net.connect` because the node's bodies contain
  `tracing` macros.
- Suggested resolution: state per rule which edge kinds it reads at
  milestone 2: SYS004 over `resolve_import` (Exact for `crate::` paths) and
  over call edges only once they are import-verified (G2 fix promotes
  `use`-qualified calls to Must); give well-known macro families a declared
  `may_define = No, may_read_scope = No` and a callee vocabulary so they do
  not poison `hi`; make shrink require `Exact` absence and print the
  blocking opaque sites. Add these as acceptance criteria on the gob-ir and
  grimble-bind tickets.

### M5. The 12 v1 binding mechanisms do not all have v2 homes; inference of `binds` needs facts U does not carry (MEDIUM)

- Where: notes/v1/strata.md lines 310-325 (B1-B12); grimble-model.md lines
  107-115; code-model.md lines 231-253 (binds inferred from attributes and
  stubs), lines 329-334 (decided: inferred, human symref canonical, SCIP
  derived); universal-model.md lines 199-203 (F4 = "comments bound to
  targets"), line 374 ("Rust today F3"); architecture.md line 252
  (grimble.toml has only strict, modeled, packs).
- What, mechanism by mechanism:
  - Become scope-graph or select queries (decidable, Exact on F1+ for
    syntax, Bounds where macros hide units): B1 `code` -> `owns` (Q32);
    B5 `interface=` -> `surface` over public_api (Q33, Bounds until G10
    re-exports); B6 flows-as-imports -> SYS004 over `resolve_import` (Q21);
    B9 vmodel `ref/runnable` -> resolve_symref (Q22) and test_items (Q35,
    NotApplicable without a test convention).
  - Need annotations: B3 -> `grimble:node/channel/boundary` attestations;
    `binds` with `via="manual"`; B2 `may ... of` argument constraints need
    `const_value` at the effect site's argument (Q24) which no adapter
    provides, so `of` is Unresolved everywhere at milestone 2.
  - Undecidable or not derivable, must be opaque/Unknown and Unresolved:
    FFI/IPC/HTTP edges (declared flows only), dynamic dispatch and
    function-pointer effects, eval/reflection, macro-generated symbols
    without expansion.
  - No v2 home: B4 (frob directives on design constructs; see H1), B10
    (`[graph].exclude`: grimble has no walk-exclusion knob, and v1
    INV-026's "fully excluded node" skip is not carried), B11 and B12
    (binding generators and `sys init`: no spec, see M10). B8 (refine) is
    deliberately dropped; say so in the migration report.
  - "Inferred" binds need the module name of a PyO3 module (from
    `#[pymodule]` plus `pyproject.toml` `module-name`), which is a build
    manifest fact; U has only `keys` (Q19) and no manifest relation, so the
    inference is May at best. Attestations bind through comments, which U
    puts at F4 while the Rust adapter is graded F3 although gob-directives
    binds Rust comments today: the fidelity ladder and the landed
    capability disagree.
  - "Human symref canonical, SCIP derived" remains coherent if identity is
    fixed as in H1; see L2 for the unstable cases.
- Why it matters: migration.md line 18 promises constructs with no v2
  equivalent "are listed, never silently dropped"; B4, B10, B11 are not
  even listed.
- Failure scenario: a v1 repo's `[graph].exclude` hid generated code; after
  `grimble migrate` the exclusion is gone, SYS003/CAP001 fire on generated
  files, and the user excuses them node by node.
- Suggested resolution: add a mapping table B1-B12 -> v2 (query,
  annotation, or Unresolved) to grimble-model.md section 4; add `[grimble]
  exclude` (materialized); state `binds` inference status as May unless the
  manifest is read, and add a `manifest` capability to the adapter tuple;
  regrade fidelity so F3 vs F4 matches what binds comments.

### M6. grimble-check would duplicate frob-check; the reusable orchestration is not in substrate, and `--only` rejects sibling families (MEDIUM)

- Where: rules.md lines 298 (`frob-check / grimble-check pipeline,
  selection, render`); boundaries.md lines 105 and 289-293 (product crates
  never depend on other products); crates/frob-check/src/pipeline.rs lines
  6-7 (imports `frob_lease`, `frob_obligations::apply_exceptions`), lines
  30-44 (`validate_only` checks `Registry::global()`), lines 63-72
  (refingerprint), line 117 (`Cache::open(&root.join(".frob"))`), line 184
  (exceptions applied by frob-obligations); crates/frob-check/src/repo.rs
  lines 27-114 (inputs digest and cached repo groups, generic but
  crate-private); exceptions.md and boundaries.md 2.5 (matching belongs to
  gob-rules); products.md line 69 ("merges findings ... through the shared
  gob-rules registry"); rules.md lines 304-305 (`gob-rules/testing` builds
  a snapshot).
- What: the generic parts of the pipeline (snapshot assembly of files and
  symbols, per-file check dispatch and cache, repo-rule groups and their
  cache key, `--only` validation, exception application, fingerprint and
  sort, timing, perf finding) live in frob-check and frob-obligations,
  entangled with leases, ledger and tickets. grimble-check may not depend
  on them, so it must re-implement all of it. In addition, without
  `bundle`, `frob check --only SYS` fails with `UnknownFamily` because
  grimble's families are not in frob's linked registry, contradicting
  "a foreign family is never unknown"; with `bundle`, user GPOL rules loaded
  at runtime by grimble are still absent from frob's registry.
- Why it matters: two pipelines drift (the v1 lesson behind D3), and the
  NO DUPLICATION rule is violated by design.
- Failure scenario: grimble ships with its own exception matcher; a
  `grimble:accept` that frob's matcher treats as file-scoped is treated as
  symbol-exact by grimble, so the same finding is suppressed in `grimble
  check` and reported in `frob check`.
- Suggested resolution: create `gob-check` (substrate) holding the
  product-neutral pipeline: `Snapshot` core (files, symbols, IR, lock),
  `FileCheck` trait and per-file cache, repo-group cache, exception
  application (moved from frob-obligations into gob-rules), `--only`
  validation against product-namespaced families including a static list
  of sibling families (a `known_families` table generated by gob-dev), and
  render; frob-check and grimble-check become thin product layers. Do this
  before grimble-check exists (ticket G06).

### M7. The "shared ack implementation" is not in gob-lock; grimble ack would copy frob-ack (MEDIUM)

- Where: boundaries.md line 61 (gob-lock owns "the shared `ack`
  implementation"); crates/gob-lock/src/lib.rs lines 1-10 ("This crate knows
  nothing about git, symbols or products ... callers decide what to
  acknowledge and how to commit"); crates/frob-ack/src/ack.rs lines 35-60
  (target resolution), 78 (`entry_for`), 180-205 (plan and commit via
  `commit_paths`); crates/frob-ack/src/inputs.rs line 20 (`PRODUCT =
  "frob"`).
- What: resolution of an ack target, building an entry from current facet
  digests, reason checking, `--all`, and committing the lock file are in
  frob-ack with the product hard-coded. cli.md line 199 assigns `grimble
  ack` to "grimble-bind on gob-lock", which today means re-writing frob-ack.
  The code-model.md lines 64-67 promise of an "append-only ack_log with old/
  new digest" is in neither crate.
- Why it matters: ack semantics are a contract users learn once; two
  implementations will diverge (for example on what acking a file means).
- Failure scenario: `frob ack src/a.rs` acks every symbol in the file
  (ack.rs lines 36-51); grimble's re-implementation acks only the file
  node; SYS007 keeps firing after the user believes they acked.
- Suggested resolution: move `plan_ack` and target resolution into
  gob-lock (parameterized by product name and entry kind, taking a
  `SymbolGraph` and a commit callback), leaving frob-ack with DRIFT/AFFECT
  rules and the verb. Decide whether `ack_log` exists and fix code-model.md.

### M8. The universal-rule authoring level targets the superseded IR, and the callee vocabulary has no owner (MEDIUM)

- Where: rules.md lines 13-15, 75-79, 147-152 (`kind = "Loop"`, `has = {
  kind = "Call", callee = "sort" }`, "callee names resolved through the
  per-language callee vocabulary"); code-model.md lines 202-224 (IrKind
  list); universal-model.md lines 3-4 (supersedes code-model section 5),
  lines 121-131 (loop/branch/return are attributes on `group`, `apply`,
  `bind`), line 350 (`callee_vocab`, "An empty vocabulary is
  NotApplicable"); boundaries.md line 100 (grimble-lints owns "callee
  vocabularies"); goals.md lines 145-147 ("adding a language is one adapter
  crate ... and zero changes to universal rules"); rules.md lines 161-167
  (engine ast-grep-core "with the IR level implemented on the same matcher
  trait"); cli.md line 165 (`frob rule test` and `grimble rule test`, owned
  by gob-rules); README D4.
- What: (a) the level-2 TOML syntax names IrKind values that U does not
  have; there is no mapping from `kind = "Loop"` to `group` with a loop role
  attribute. (b) If vocabularies live in grimble-lints, adding a language
  edits grimble-lints, violating the scaling rule; they belong with the
  adapter (its `cap_L`), and capability detectors and PROC001-style frob
  rules need them too. (c) If the shared declarative engine (levels 1 and 2)
  sits in gob-rules so `frob rule test` can run it, frob links gob-ir and
  ast-grep-core, contradicting D31 ("only IR code stays out of frob's
  build"). (d) The decision log has no row accepting U, so D4 and
  code-model section 5 are still normative and implementers will build the
  IrKind matcher.
- Why it matters: GPOL is the owner's "natural and powerful" extension
  point; writing it against the wrong IR wastes the milestone.
- Failure scenario: a user writes `language = "*"`, `kind = "Loop"`; on a
  Verilog `generate for` (U: `group` with `Loop{Elab}`-like role) the rule
  fires as a runtime loop, the exact PERF false positive
  lint-requirements.md line 303 warns about.
- Suggested resolution: record U acceptance as a D-row; rewrite rules.md
  section 3 level 2 over U roles (`role = "loop"`, `apply` with `callee` via
  vocabulary, `loop_kind != elab`); put vocabularies in the adapter
  (gob-languages data per language, queried through Q47); place the
  declarative engine in a `gob-pattern` crate that only grimble links, and
  have `frob rule test` cover POL only.

### M9. Data packs and the registry drift-lock are under-specified and break D28 and "no invisible variables" (MEDIUM)

- Where: grimble-model.md lines 156-173; boundaries.md line 104
  (grimble-packs: "pack loader and schema"), line 132 (REG and DEC are
  frob-obligations); architecture.md line 252 (`packs` materialized "no",
  default empty); monorepo.md line 39 (`packs/` in this workspace, i.e.
  shipped); README D22 ("no invisible variables"); notes/v1/strata.md lines
  726-764 (v1 drift-lock and its REG001-012 rules).
- What:
  - Pack format: "TOML packs" contributing "atoms, detectors, obligations,
    rule parameters" with no schema; detectors' pattern language is
    unstated (ast-grep in the target language? U `ir_pattern`?); obligation
    discharge needs claim rungs (`require proof >= L3`), which the v2
    grammar does not carry; a pack's "marker plus evidence" rule needs a
    family id, and REL is already frob's release family (rules.md line 107),
    so v1 REL2xx cannot keep its prefix.
  - In U terms a pack is a structured-data artifact (Q19 `keys`) with
    embedded code islands (Q18) for its patterns; it needs its own adapter
    (F2: units = pack rows, references = atom ids) so PARSE findings, spans
    and digests exist for pack files, but nothing says so.
  - Invisible variables: `packs` is not materialized, and pack content
    ships inside the binary, so a grimble upgrade changes detectors and
    obligations with no repo-visible diff.
  - Drift-lock: "Rows whose deferred ticket closes go red" needs ticket
    state, which grimble may not know (D28); REG is frob's family; the
    registry's file location, format, owning crate and rule ids are unnamed.
- Why it matters: packs carry threat, PII and reliability, the parts v1
  users asked to keep as data.
- Failure scenario: grimble 2.1 adds a detector to the `threat` pack; CI on
  an unchanged repo turns red with new CAP003 findings and the repo shows
  no change that explains it.
- Suggested resolution: write `docs/design/grimble-packs.md`: TOML schema
  with `deny_unknown_fields` and a generated JSON schema, pattern syntax =
  the GPOL pattern syntax, a pack adapter at F2, family prefixes per pack
  (`THREAT`, `RELY`, `PRIV`), pins `packs = ["threat@1"]` materialized in
  grimble.toml with a census on version change (Advisory for one release,
  same as new atoms), and the drift-lock row's `deferred` disposition
  emitted with an opaque ticket in `--json` and evaluated by frob, as
  exceptions are (EXC-style). Name the owning crate (grimble-packs) and
  the ids.

### M10. Adoption path and verb surface are not designed end to end (MEDIUM)

- Where: cli.md lines 198-203 (grimble verbs), line 165 (`rule test`);
  products.md lines 42-45 ("starts with the model-free lints and grows into
  the model"); boundaries.md lines 105-106; universal-model.md line 205
  (`frob doctor --languages` prints fidelity); grimble-model.md line 105
  (`grimble shrink`), migration.md line 18 (`grimble migrate` emits
  `.grmb`); notes/v1/strata.md line 325 (B12 `frob sys init`).
- What: nothing says what `grimble check` does in a repo with no
  `design/` (skip SYS/CAP silently, or one Advisory "no model"?), what
  `grimble init` writes (grimble.toml with materialized knobs only, or a
  skeleton model of one node per crate and one flow per observed import
  direction as v1 B12 did, which conflicts with "never auto-widen" unless
  stated as a one-time bootstrap without `may`), or which model-free rule
  gives the first useful finding (CYCLE over imports is the only candidate
  at milestone 2, and grimble-arch has no ordering). Verbs without an owner
  or missing: `grimble doctor --languages` (fidelity; only frob has doctor),
  `grimble exceptions list` (the audit view is frob-only, so a
  grimble-only user cannot list their exceptions), `grimble rule test` is
  not in grimble's row, `grimble schema`, `grimble fmt`. `shrink` and
  `migrate` must write `.grmb`, but grimble-model has no printer or
  format-preserving editor; `check --census capabilities` is a flag with no
  owner beyond grimble-check.
- Why it matters: the owner's adoption claim ("one binary makes that a
  config change") has no path a user can follow in under a minute.
- Failure scenario: `grimble init && grimble check` in a Rust repo prints
  nothing (no model, no CYCLE yet); the user concludes grimble does
  nothing.
- Suggested resolution: specify: `grimble init` writes grimble.toml and a
  skeleton `design/<repo>.grmb` with one node per workspace member and
  `owns`, flows from current import directions, no `may`, plus a header
  comment saying it is a one-time bootstrap; `grimble check` without a
  model runs model-free families and prints one Advisory "no model; SYS
  and CAP not evaluated"; first finding = CYCLE001 and SYS004 against the
  skeleton. Add `doctor`, `exceptions list`, `rule test`, `schema`, `fmt`
  rows with owners; give grimble-model a printer (round-trip tested).

### M11. Standalone and orchestrated runs: cache location, double parse, time budget, and scoping flags are unstated (MEDIUM)

- Where: crates/frob-check/src/pipeline.rs line 117 and
  crates/frob-ack/src/rules.rs line 338 (cache at `<root>/.frob`);
  crates/gob-cache/src/lib.rs line 140 (`Cache::open(dir)`); rules.md
  lines 186-191 (`--ticket` narrows to the ticket's files plus hops), lines
  206-211 (2 s warm budget; external tools outside it); git-io.md line 72
  (one sibling spawn per check); cli.md line 198 (no grimble flags listed).
- What: standalone grimble needs a cache directory (`.grimble/`? reuse
  `.frob/`?); if separate, an orchestrated `frob check` parses the repo
  twice (frob in-process, grimble in the spawn), and a cold grimble run is
  3-6 s, so the land path's synchronous check either breaks its budget or
  the sibling stage is silently "outside the budget" like tools. `frob check
  --ticket X` must pass the scoped file set and `--base` to the sibling, but
  `grimble check --files/--base` are not specified, and grimble has no
  notion of hops over a ticket.
- Why it matters: land latency and scoped-check correctness are frob's
  core promises (D8, D30).
- Failure scenario: `frob land` on a one-file change spawns `grimble check
  --json` over the whole repo with a cold cache because grimble writes
  `.grimble/`; land takes 8 s on every ticket.
- Suggested resolution: share the parse cache (`.frob/cache.sqlite` is
  product-neutral by key; rename the dir to a neutral `.gob/` or document
  that grimble reads `.frob/` when present and `.grimble/` otherwise);
  specify `grimble check --files F.. --base REF --json`; state the sibling
  stage's budget class in rules.md section 4.

### M12. Selectors are claimed by three owners and implemented by none (MEDIUM)

- Where: boundaries.md line 57 (gob-walk owns "selectors (`path::qual`
  globs)"), line 96 (grimble-model owns selectors `owns`, `surface`, `at`);
  lint-requirements.md line 259 (Q32 `select`/`owner`, "most specific
  wins"); grimble-model.md lines 63-66; crates/gob-walk/src (no selector
  type; grep finds none).
- What: selector syntax (path glob, `::qualname-glob`, kind filter,
  optional language), specificity order (symbol > file > dir; what about
  two globs of equal depth with different wildcards?), and the Bounds
  semantics over May units are not defined anywhere and not landed. frob's
  leases (symbol sets, M2), crunk globs and grimble owns all need the same
  function.
- Why it matters: SYS001, SYS002, SYS003 and FOREIGN are all defined by
  specificity; an informal definition yields different owners in
  different tools.
- Failure scenario: `owns "src/**"` on node a and `owns "src/*/mod.rs"` on
  node b; "most specific" is undefined for globs of different shapes, so
  `src/x/mod.rs` is SYS002 in one implementation and owned by b in another.
- Suggested resolution: define selectors once in gob-walk (grammar plus a
  total specificity order: literal segments count, then `*`, then `**`,
  then qualname depth, then kind filter), implement Q32 there over U units
  with Bounds, and make grimble-model parse selector strings with that
  crate.

---

## 3. LOW

### L1. The V-model chain names tickets, which grimble cannot know (LOW)

- Where: grimble-model.md lines 186-188 ("requirement -> design decision ->
  ticket -> test, all symbols, all checked").
- What: tickets are frob's; the V-model in grimble can only reach tickets
  through frob's `implements` link read from `grimble graph --json`.
- Scenario: an implementer adds a ticket node kind to the V-model schema.
- Resolution: reword to "requirement -> design -> test in grimble; frob
  joins tickets to V-model entities through `implements`".

### L2. SCIP derivation is unstable for anonymous and multi-part units (LOW)

- Where: code-model.md lines 331-334; universal-model.md lines 150-154
  (anonymous units: positional index, open question 2).
- What: SCIP symbols need a package and version (Q23 `package_of`; version
  unknown in a workspace) and stable descriptors; positional anonymous
  units change id when siblings reorder.
- Scenario: an exported `binds` edge to a closure-defined handler changes
  SCIP id on an unrelated insertion; external indexes break.
- Resolution: export SCIP only for named units, mark others `local`, and
  use `.` for unknown versions as SCIP allows.

### L3. Rollup key of Unresolved is stated three ways (LOW)

- Where: code-model.md line 284 (one per node); lint-requirements.md lines
  152-155 (per rule, language, scope); grimble-model.md lines 145-147 (one
  per node, not per cell).
- Resolution: one key, `(rule, node or scope, language)`, stated in
  gob-rules; H4's cell set uses it.

### L4. Directive vocabulary lists disagree (LOW)

- Where: lint-requirements.md line 124 (R37: `grimble:binds/node/channel/
  effect/may/excuses`); grimble-model.md line 115 (node, channel,
  boundary, effect); code-model.md line 239 (`binds`).
- What: `grimble:may` and `grimble:excuses` exist in one list only;
  `grimble:boundary` is missing from R37.
- Resolution: one table of grimble directives in grimble-model.md section
  4, generated reference from the derive.

### L5. U is not in the decision log; superseded text is still normative (LOW)

- Where: README.md D4 line 66 ("universal over a structural IR"); README
  table line 30 (U as DRAFT); code-model.md section 5; rules.md line 75.
- Resolution: add a D-row when U is accepted, mark code-model section 5
  superseded, and update rules.md references.

### L6. Spanless findings lose their anchor when re-fingerprinted (LOW)

- Where: crates/frob-check/src/pipeline.rs lines 59-72 (anchor replaced by
  the file path or empty string); crates/gob-rules/src/finding.rs lines
  23-31.
- What: grimble's entity-level findings (CAP003 per node, SYS005 per flow,
  Unresolved rollups) have no file span; after refingerprint their anchor is
  "", so two with the same normalized message (digits become `#`) share a
  fingerprint and a baseline key.
- Scenario: two flows `f_1`, `f_2` both report "flow f_# has no producer";
  baselining one baselines both.
- Resolution: keep a logical anchor (entity id) on `Finding` and use it in
  refingerprint when there is no span.

### L7. SARIF and JSON have no logical location for model entities (LOW)

- Where: rules.md lines 314-316 (SARIF in 2.0); gob-diagnostics
  FindingRecord (file, line, column only).
- Resolution: add `entity` to FindingRecord (H3) and map it to SARIF
  `logicalLocations`.

---

## 4. What grimble needs from U that universal-model.md does not provide

1. An identity that survives body edits, distinct from the content hash
   (H1). U 2.2 must separate identity (adapter-stable, default symref) from
   the rename key (content hash).
2. A `.grmb` adapter and, generally, an adapter for data-pack and config
   artifacts that carry entity declarations (H1, M9).
3. Selector and owner semantics (Q32) with a total specificity order and
   Bounds over May units (M12). U section 5 lists `select/owner` but 4.4's
   capability table does not, and no theorem covers it.
4. The atom registry in substrate, the detector registry, and a query
   `detectors(lang, atom)` exposing `cap_L` to rules; a cell distinction
   between NotApplicable, unmeasured and unknown-by-design (H4).
5. Ownership of `binds`: U 4.4 line 291 lists `binds` as an adapter
   capability and Q36 says "grimble supplies"; frob's AFFECT and evidence
   reach consume it. Decide: inference of binding attributes is an adapter
   capability (substrate, any product), the cross-language pairing and
   BIND rules are grimble, and frob gets pairs only via `--json` (D28).
6. A sig-normalization member in the adapter tuple (`sig_L` mapping to the
   Type lattice, Q39) and a canonical `norm_sig` stream for contract digests
   (H2); A_L = (parse, rho, bind, cap) has no place for it.
7. Argument values at effect sites for `may ... of` constraints: Q24
   `const_value` exists but there is no query joining an effect site to its
   argument expressions (M5).
8. A manifest relation (crate and package names, PyO3 module names, workspace
   members) for binds inference and for `grimble init` skeletons (M5, M10).
9. Precision targets per adapter tied to rules: which rules become
   non-Unresolved at which precision (M4). Fidelity F3/F4 should be checked
   against what the landed adapters bind (comments are bound on Rust today
   although Rust is graded F3).
10. `subjects_examined` and `polarity` on the rule and finding types
    (gob-rules), named in U section 8 but absent from crates/gob-rules
    (meta.rs has no polarity; Finding has no subject count).
11. Polarity for CAP003, which is neither P+ nor P- over U facts: it is a
    completeness check of the model against the applicability set from item
    4; U should name this shape (model completeness, `grm` side input joined
    to `cap_L`).

---

## 5. Proposed milestone-2 cut for grimble (assumes gob-ir lands first)

Assumption: T-IR (gob-ir: U terms, scope graph with status, answer lattice,
evaluator, Rust and markdown adapters re-expressed over U, G1-G4 and
G10-G19 fixed) is done. Ids below are placeholders (G01...); points use the
milestone-1 scale.

| # | Ticket | Crate(s) | Pts | Blocked by |
|---|---|---|---|---|
| G01 | Design: `.grmb` specification (EBNF, lexical rules, scoping, fragments, version header, unit table, selector and atom grammar, unified exception syntax and node-scoped matching) | docs only (grimble-model.md) | 5 | U accepted (D-row) |
| G02 | Design: binding semantics over U (relation with status, identity vs digest, polarity per SYS/CAP/BIND id, F0/F1 behaviour, B1-B12 mapping, matrix cell set, missing ids: CLAIM, VMOD, GRMB, SYS010-012) | docs only | 5 | G01 |
| G03 | Design: sibling JSON contract `grimble.check/1` and `grimble.graph/1`, gate behaviour for missing sibling, `--files/--base` passthrough, cache sharing | docs only (boundaries.md or new file) | 3 | G02 |
| G04 | Design: packs and drift-lock (schema, pins, family prefixes, opaque deferred dispositions) | docs only | 3 | G02 |
| G05 | Canonical facet streams (G7-G9), Attr facet, `digest_scheme` in gob-lock, typed lock entries (symbol, flow), ack planner moved from frob-ack to gob-lock | gob-symbols, gob-lock, frob-ack | 8 | T-IR, G02 |
| G06 | Extract product-neutral pipeline: `gob-check` (snapshot core, file and repo rule caches, `--only` with known sibling families, render); exception application moved to gob-rules; rule `polarity` and `subjects_examined` | gob-check (new), gob-rules, frob-check, frob-obligations | 13 | T-IR |
| G07 | Selectors: grammar, specificity order, `select`/`owner` over U with Bounds | gob-walk (or gob-ir) | 5 | T-IR, G01 |
| G08 | grimble-model: lexer, parser with spans, fragments, model-load errors, JSON export, printer and `fmt`, U adapter A_grmb, editor grammar from keyword table | grimble-model | 13 | G01, G07 |
| G09 | grimble binary skeleton: grimble-check over gob-check, `check --json --files --base`, `init` (grimble.toml, skeleton model), `doctor --languages`, `schema`, `exceptions list`, model-free run | grimble-check, grimble (bin) | 8 | G03, G06, G08 |
| G10 | grimble-arch: CYCLE (imports, Pc), LARGE (Pn), DEAD (P-) over U; first model-free findings | grimble-arch | 8 | G09 |
| G11 | grimble-bind 1: owns/surface resolution, FOREIGN, SYS001-005, SYS009, SYS010-012 attestations, import-level SYS004 with polarity; G2 import-verified call promotion | grimble-bind, gob-symbols | 13 | G02, G07, G09 |
| G12 | grimble-bind 2: grimble.lock, `grimble ack` on the gob-lock planner, SYS006 over norm_sig, SYS007, SYS008 | grimble-bind | 8 | G05, G11 |
| G13 | frob orchestration: sibling stage (spawn and `bundle`), schema check, gate behaviour for missing sibling, ticket-bound exits and close guard from grimble JSON, `implements design:` validation | frob-check, frob-obligations, frob-ledger | 8 | G03, G09, G06 |
| G14 | grimble-capabilities: atom and detector registries in substrate, Rust detectors (fs, net, exec, env) via callee vocabulary, matrix with the H4 cell set, CAP001-003, census | gob-ir (atoms, vocab), grimble-capabilities | 13 | G11, G02 |
| G15 | `grimble shrink` (Exact-absence only, prints blocking opaque sites) and exceptions on nodes with attestation | grimble-bind, grimble-capabilities, grimble-model | 5 | G14, G08 |
| G16 | grimble-kernel port: closure, age, demand, V-model closure, claims and assumes; CLAIM and VMOD families | grimble-kernel | 8 | G08, G02 |
| G17 | ast-grep spike outcome applied: `gob-pattern` engine, GPOL level 1 (per grammar) and level 2 (over U roles), `grimble rule test` | gob-pattern (new), grimble-lints | 13 | T-IR, ast-grep spike (audit M26), G09 |
| G18 | `grimble migrate` from v1 `.strata` with the B1-B12 report | grimble-model | 8 | G08, G14 |
| G19 | grimble-serve MCP (design queries) | grimble-serve, gob-serve | 5 | G09, gob-serve |

Deferred past this cut (record as dropped-for-now tickets with a reason):
grimble-packs and pack families (after G04 and G14), grimble-security,
grimble-vet and `vet --hook`, cross-language `binds` adapters (need a
Python or TS adapter first), SARIF (gob-diagnostics, before 2.0 release).

Critical path: T-IR -> G01 -> G02 -> G07 -> G08 -> G09 -> G11 -> G14 (about
70 points). The first user-visible value is G10 (model-free CYCLE) right
after G09, which answers M10's "first useful finding".

---

## Notes

Checked and found consistent (no finding):

- D28's core boundary is stated identically in products.md, boundaries.md
  (sections 1, 3.2, 3.9, 6), exceptions.md section 1, grimble-model.md
  section 7, code-model.md section 6 and tickets.md line 212: grimble never
  reads frob.lock or tickets; frob reads grimble only through `--json`.
- One lock file per product is implemented as designed at the format
  level: `gob_lock::file_name(product)`, sorted TOML, atomic save, a
  missing file is an empty lock (crates/gob-lock/src/file.rs).
- gob-directives is namespace-parametric as boundaries.md says
  (`ScanConfig{namespaces, product}`, crates/gob-directives/src/scan.rs
  lines 22-37), and PARSE/DSL findings are emitted under the configured
  product (D32).
- gob-exec already has `Program::Sibling` resolving beside `current_exe`
  first (D52), so the sibling spawn has a home.
- Family ownership table boundaries.md 2.5 covers every grimble family
  named in rules.md section 3 (the gaps are outputs with no family, M3).
- `RuleMeta` carries a `product` field, so product namespacing of rule ids
  has a landed hook.
- CAP003's Advisory-for-one-release and SYS003's opt-in (audit M16) are
  stated consistently in code-model.md and grimble-model.md.

Skimmed or not verified:

- notes/research/paradigms.md and calculi.md were read only at the
  detector-kind passage and through universal-model.md; the theorems'
  citations (`[verify]` tags) were not checked.
- notes/v1/strata.md sections 3.3-3.6 (claim procedures, evidence,
  boundary, entity) and 7.2 (scenarios) were skimmed; the kernel port scope
  in G16 rests on grimble-model.md section 3 and strata.md section 3.2.
- gob-symbols `graph.rs` and `rust.rs` were read only at the API level;
  gap claims G1-G19 are taken from lint-requirements.md section 9 (spot
  checked: CallEdge, public_api, Digests).
- frob-check's snapshot.rs, filecheck.rs and frob-obligations' exception
  code were not read line by line; M6 rests on the imports and call sites
  in pipeline.rs and repo.rs.
- crunk was out of scope except where it shares substrate.
- Nothing was executed (no cargo, no frob) per the task constraints.
