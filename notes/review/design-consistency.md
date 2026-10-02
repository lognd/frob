# Design-set consistency audit after the U, NEAT, CI/DK and grimble-9 drafts

Status: audit findings only, 2026-10-02, branch `experimental` at 0683c0a91.
Nothing was run (no cargo, no frob); every claim about code is by reading
the files cited. Subject: docs/design/universal-model.md (U),
neatness.md, cicd.md, grimble-model.md section 9, README rows D56-D60,
checked against the older design files, README D1-D55, the research
and review notes, and the landed crates.

Counts: 12 HIGH, 24 MEDIUM, 9 LOW (45 findings).

Severity key: HIGH = a contradiction an implementer would hit;
MEDIUM = a gap or duplication; LOW = wording.

---

## HIGH

### H1. code-model.md section 5 (IrKind) is still normative and every reference to it contradicts U (HIGH)

- Where: code-model.md:202-229 (`IrNode`/`IrKind`, "Unmapped kinds become `Other`"),
  code-model.md:96-97 (gob-ir "IrNode, IrKind, ir_map"), code-model.md:116 (`ir_map`
  adapter member), code-model.md:21-22; boundaries.md:51 (gob-ir row), boundaries.md:99-100
  ("detectors over the IR", "universal rules over the IR"); rules.md:75-79, rules.md:147-152
  (level-2 rules use `kind = "Loop"`, `kind = "Call"`), rules.md:163-165; grimble-model.md:142
  ("IR patterns"); goals.md:135-148 ("adapter crate (grammar, symbol extractor, IR mapping)");
  README.md:71 (D4), README.md:98 (D31). Versus universal-model.md:3-4 ("Supersedes
  code-model.md section 5 when accepted"), :100-121 (Sigma_U), :167-170 (rho_L default clause
  is `opaque`, unmapped kinds are a build-time finding), :500-504.
- What: U replaces `IrKind` with 13 sorted operators, a scope graph and `opaque` as the default,
  but code-model.md 5 still says unmapped kinds become `Other` with `ts_kind` (a silent
  catch-all, not an opaque node with a reason), and rules.md's universal-rule syntax addresses
  `Loop`/`Call` kinds that do not exist in Sigma_U (loop is an attribute on `group`, U 2.4).
- Failure: an implementer of gob-ir or of a level-2 GPOL rule follows rules.md:149 and
  writes `kind = "Loop"`; there is no such operator, and an unmapped node read as `Other`
  lets a P+ rule certify clean what U says is Unknown.
- Fix: replace code-model.md 5 with a three-line pointer to universal-model.md 2-5; rename the
  adapter member `ir_map` to `rho` (signature morphism) plus `bind` and `cap` (U 3.1); rewrite
  rules.md:147-152 to address U operators and role attributes (`group[role=loop]`,
  `apply[kind=call] callee=sort`); update boundaries.md:51 and the D31 row (H2); amend
  goals.md:146-148 to "adapter (parse, rho, bind, cap) plus a fidelity corpus".

### H2. gob-ir's place in the layering and "frob builds without gob-ir" (D31) are false under U (HIGH)

- Where: architecture.md:37-38 (gob-ir depends on "symbols"); code-model.md:96-97 ("frob
  builds without it"); boundaries.md:265 ("only IR code stays out of frob's build"); README.md:98
  (D31 "gob-ir holds only the structural IR"). Versus universal-model.md:502-509 (gob-symbols
  "becomes the Rust and markdown F3/F4 adapter over U", gob-ir holds the evaluator, lattice
  types and canonical facet stream), universal-model.md:512-513 (gob-rules uses the lattice),
  cicd.md:141-146 (frob's CI/DK rules are "adapters in U"), grimble-model.md:238-239 (digests
  over U's canonical facet stream).
- What: if gob-symbols produces U terms, gob-symbols depends on gob-ir, the reverse of
  architecture.md:37. And frob then links gob-ir: DRIFT/AFFECT digests (canonical facet
  stream), COV (polarity over May edges, U 5), CI and DK (U adapters) all need it.
- Failure: an implementer adds `gob-ir = { path }` to gob-symbols per U 8 and the layering
  rule enforced over Cargo metadata (architecture.md:28-29) rejects it, or keeps gob-ir above
  gob-symbols and creates a dependency cycle.
- Fix: rewrite architecture.md:34-42 order as `gob-text`, `gob-macros` < `gob-ir` (types,
  lattice, evaluator; text only) < `gob-languages` < `gob-symbols` (adapters); delete "frob
  builds without it" (code-model.md:97, boundaries.md:265) and restate D31 as a new D-row:
  "gob-ir is a substrate core every product links from milestone 2".

### H3. Whether Unresolved can fail the gate is answered four different ways (HIGH)

- Where: crates/gob-diagnostics/src/exit.rs:33-41 (`f.severity != Severity::Unresolved`:
  Unresolved never fails); crates/gob-rules/src/meta.rs:7-18 (`Unresolved < Advisory`);
  rules.md:25-28 and rules.md:200-202 (step 8: fail only at or above `--fail-on`); rules.md:184-187
  and boundaries.md:32-35, :298-301 (missing or mismatched sibling = one Unresolved finding);
  products.md:109-111 ("refuses a sibling whose `--json` has another `schema_version`");
  cli.md:69 (schema mismatch is exit 3 needs-action); grimble-model.md:272-277 (absent sibling
  "fails the gate by default", `[check] require_siblings = true`, "Severity ordering is
  amended so that Unresolved can fail when a rule declares it must"); universal-model.md:242-246
  (subject accounting) gives no declaration that a rule "must" fail.
- What: the landed evaluator, the pipeline text and the exit table all make Unresolved
  non-failing; 9.5 says otherwise but names no mechanism (no RuleMeta field, no fail_on value,
  no exit row), and the schema-mismatch case is simultaneously an Unresolved (exit 0), a refusal
  (exit 3) and a gate failure (exit 1).
- Failure: grimble review H3's scenario stands: grimble.toml present, binary absent,
  `frob check --fail-on error` exits 0 and `frob land` lands an undeclared `net.connect`.
- Fix: decide once in cli.md section 2 and record a D-row: add a `fails_unresolved: bool`
  (or `unresolved = "fail" | "report"`) field to the Rule derive, default `report`; sibling-missing
  and schema-mismatch are rule ids (e.g. CHECK001, CHECK002) with `fails_unresolved` true when
  `[check] require_siblings`; change exit.rs:40 to count such findings; add an exit-table row
  "Unresolved from a rule that declares it must fail: 1"; make products.md:111 and cli.md:69
  say the same; update rules.md step 4 and step 8.

### H4. U contradicts itself on NotApplicable: skip, Unresolved, or shown as such (HIGH)

- Where: universal-model.md:222-224 (NotApplicable "so rules can skip rather than nag");
  :242-246 (zero subjects, "every query answered Unknown or NotApplicable", reports Unresolved);
  :469-471 (Brainfuck: every rule NotApplicable "which the report shows as such");
  :516-517 ("an `n/a` cell is a declared Unknown ... reported as Unresolved");
  notes/research/lint-requirements.md:152-155 (NotApplicable rolled up to ONE Unresolved per
  (rule, language, scope)); grimble-model.md:279-291 (no not-applicable cell at all).
- What: three outcomes for the same answer. Under 4.2 a COV001 run on a CSS-only repository
  is Unresolved; under 4.1 it is skipped (clean); under 6.1 it is a third report state that the
  severity lattice (Error/Warn/Advisory/Unresolved) does not have.
- Failure: an implementer of the gob-rules polarity framework cannot write the case arm for
  "all subjects NotApplicable"; either every Markdown-only repository carries permanent
  Unresolved for every code rule (nag), or the "no test convention" silent pass 4.2 was
  written to close reopens.
- Fix: in universal-model.md 4.2 state: Unknown subjects count as unexamined (Unresolved);
  NotApplicable subjects are excluded from the subject set; a rule whose whole scope is
  NotApplicable reports nothing and the per-language fidelity report (H5's sibling/fidelity page)
  lists it as not applicable. Delete "an n/a cell is a declared Unknown" (:516) and fix
  lint-requirements 3.1 to match, marking the note superseded on this point.

### H5. U 4.6 says a P+ rule "stays silent" on opaque subjects; U 4.2 says it may certify clean only when hi has no offender (HIGH)

- Where: universal-model.md:354-357 ("a P+ rule stays silent on an opaque subject (it cannot
  prove an offender)"); universal-model.md:235-236 (P+ "clean only if `hi` contains none");
  notes/research/lint-requirements.md:161 (P+ else-branch: "Unresolved, listing hi minus lo");
  owner requirement "anything incomputable fails loudly as opaque" (U 3.2 :189-191).
- What: "silent" on an opaque subject is a clean certification, which 4.2 forbids (hi of an
  opaque subject is the universe). The P- side is loud, the P+ side is not.
- Failure: a Rust module whose handlers come from an unexpanded proc macro (`phase`, opaque)
  contains a forbidden import inside the generated code; INV002 (forbidden import, P+) and
  NEAT013 (ambient-source-call, P+) report nothing and the file reads clean.
- Fix: universal-model.md:354-357 should read "a P+ rule reports no Error or Warn on an opaque
  subject and reports one Unresolved (rolled up per rule and artifact) naming the reason code";
  only a P+ rule whose scope contains no opaque subject certifies clean.

### H6. Rule metadata in rules.md and the landed RuleMeta lack polarity, subject count and query needs (HIGH)

- Where: rules.md:35-59 (derive example: id, family, severity, tier, scope, fix,
  `inputs(graph, docs)`); crates/gob-rules/src/meta.rs:51-80 (RuleMeta has no polarity, no
  subjects); crates/gob-dev/src/render/rules.rs:100-110 (page fields: severity, tier, scope...);
  docs/reference/rules/COV001.md (no polarity row). Versus universal-model.md:229-246, :512-513
  (derive gains `polarity`); grimble-model.md:268-270, :312-313 (polarity and subject count on
  Rule and Finding, in sibling JSON); neatness.md:88-109 and cicd.md:106-108 (every rule names a
  polarity); notes/research/lint-requirements.md:188-197 (`needs(Q..)` replaces `inputs`, third
  fixture for a feature-lacking language).
- Failure: the first NEAT or CI rule written against rules.md has no way to declare P- and the
  framework has no field to apply the U 4.2 table; findings reach the sibling JSON without the
  subject count 9.5 requires.
- Fix: rules.md section 2: add `polarity = P+ | P- | P0 | Pn | Pc` (required), replace
  `inputs(...)` with `needs(Q::...)`, state that `Finding` and the rule outcome carry
  `subjects_examined`; extend the pair-fixture doctrine to three fixtures (fires, clean,
  feature-lacking language gives Unresolved); add a gob-dev page row "polarity" and "needs";
  record it in the D-row for H3.

### H7. NEAT has no owner, and the placement test assigns NEAT and CI/DK to grimble while cicd.md says frob (HIGH)

- Where: neatness.md (no product or crate named anywhere; :113-116 "frob binds that tool's
  finding ... under the NEAT id"); cicd.md:141-143 ("CI and DK are frob families (work
  accounting of the repository's own automation)"); boundaries.md:21-24 (a rule that "still
  makes sense in a repository with no tickets, no docs policy and no release process ... is
  grimble"); products.md:12 (frob "never ... lint code style"), products.md:13 (grimble owns
  "universal and language-specific structural lints ... security patterns"); boundaries.md:129-151
  (family table "covers every family named in any design file" has no NEAT, CI, DK rows);
  README.md:5-7 (products.md and boundaries.md win over later files).
- What: NEAT002 parameter-count or NEAT004 nesting-depth are code-style structural lints with no
  ticket join; CI001 pinned-ref and CI007 injection are structural security patterns. By the
  authoritative placement test they are grimble; cicd.md says frob without amending the test,
  neatness.md is silent. README precedence makes products.md win, so cicd.md 6 loses.
- Failure: an implementer filing the first NEAT ticket cannot choose a crate, a config file
  (`[neat]` in frob.toml or grimble.toml) or a directive namespace (`frob:effects` vs
  `grimble:effect`, see H10).
- Fix: decide in a D-row and add rows to boundaries.md 2.5: either (a) NEAT, CI, DK are grimble
  (crates `grimble-neat`, `grimble-ci`; knobs in grimble.toml; directives `grimble:`), which
  matches the placement test, or (b) amend boundaries.md:21-24 and products.md:12-13 with a
  stated exception ("rules over the repository's own automation are frob"). Name the crate in
  neatness.md section 5 and cicd.md section 6.

### H8. Digest normalization has two authoritative statements and no stated transition (HIGH)

- Where: code-model.md:60-63 (BLAKE3 of whitespace-collapsed text), README.md:110 (D43),
  crates/gob-symbols/src/lib.rs:7-8 and src/model.rs:114 (`collapse_ws`), crates/gob-lock/src/file.rs:8-9
  (`LOCK_VERSION` versions the format only), file.rs:61-79 (three facets). Versus
  universal-model.md:380-382 (four facets Sig/Body/Doc/Attr over a canonical facet stream),
  :476-498 (G7-G9 "must be settled before any consumer repository commits a `frob.lock`"),
  grimble-model.md:235-239 (`digest_scheme` separate from the format version; scheme change makes
  every entry "REATTEST"); migration.md:15 (`frob migrate` re-emits consumer `frob.lock` with
  recomputed digests); code-model.md:78-79 (`norm_sig` "never used for digests").
- What: two schemes, no D-row superseding D43, no statement of which ships first, and the
  migration path writes consumer locks with whichever scheme exists at the time. The Attr facet
  also changes the facet set that DRIFT001 ("one finding per facet", D49) and `frob:describes
  (facet)` (code-model.md:172) enumerate.
- Failure: migration step 3 (migration.md:30-31) runs `frob2 migrate` on typani with
  milestone-1 digests; G8 lands later and every acked symbol in typani drifts at once with no
  `digest_scheme` field to say why.
- Fix: one D-row "digest scheme v2 = canonical facet stream, four facets; D43 is scheme v1";
  add `digest_scheme` to gob-lock now (default 1 for existing files) so the transition is
  detectable; state in migration.md section 2 that consumer migration is blocked on scheme v2;
  update code-model.md:60-63 to a pointer to U 7; reword grimble-model.md:237 to "every entry
  becomes stale (DRIFT, re-ack required)" since REATTEST is an exception state (M20).

### H9. A .grmb adapter inside grimble-model cannot feed frob rules, yet 9.3 says every frob rule works on the model (HIGH)

- Where: grimble-model.md:243-252 (grimble-model owns A_grmb; "every frob rule that works on
  code works on the model (DRIFT ..., REF from an entity to a ticket)"); boundaries.md:291-296
  (products never depend on each other; gob-* depends only on gob-*); code-model.md:86-90
  (`Language` enum in gob-languages is closed); README.md:95 (D28: frob consumes grimble only
  through `--json`); code-model.md:17 (directive DSL in .grmb files).
- What: frob cannot link grimble-model, and a substrate Language enum cannot name a product
  adapter, so frob sees `.grmb` as F0 opaque (or, today, as an empty file, U G19). 9.3 does not
  say that `grimble graph --json` exports the U term or which frob rule consumes it.
- Failure: `// frob:doc docs/arch.md#cli` above `node cli` in design/frob.grmb is never bound;
  DOC and REF report nothing (or Unresolved if H5 is fixed) although 9.3 promised they work.
- Fix: either move the .grmb parser and adapter to a substrate crate (`gob-grmb`, allowed
  because it has no product logic) and register it in an open adapter registry, or state in 9.3
  that frob binds `frob:` directives in .grmb only from `grimble graph --json` entities with
  spans and facet digests, and name that schema next to sibling.json. Replace the closed
  `Language` enum with an inventory registry either way.

### H10. Two effect vocabularies, two effect directives and three callee-vocabulary homes for one `effects` capability (HIGH)

- Where: neatness.md:61-71 (`frob:effects` atoms `fs`, `net`, `clock`, `rng`, ... and a
  `[neat.effects]` callee table per language); grimble-model.md:115 (`grimble:effect ATOM
  because`), grimble-model.md:32-34 (atoms `fs.read`, `net.connect:host`), grimble-model.md:286-290
  (atom registry in a shared gob-* crate); code-model.md:176-181 (`grimble:effect`),
  code-model.md:262-270 (atoms as a closed `Capability` derive in grimble-capabilities);
  universal-model.md:288 (`effects(region)` is one U capability), :384 (`callee_vocab` query);
  rules.md:75-76 ("callee vocabulary table keyed by language"); boundaries.md:100 (callee
  vocabularies in grimble-lints).
- What: `effects(unit)` must return Bounds over one atom set; NEAT's `fs` and grimble's
  `fs.read`/`fs.write` are different granularities of the same observation, written in two
  namespaces with two callee tables (`[neat.effects]` vs grimble detector registry).
- Failure: a function annotated `frob:effects none` that calls `std::fs::write` is CONTRADICTED
  under NEAT's table while grimble's CAP001 fires on `fs.write` from a different detector; adding
  `tokio::fs` to one table leaves the other silent.
- Fix: one atom registry in substrate (gob-ir or a new `gob-effects`), hierarchical atoms
  (`fs` covers `fs.read`/`fs.write`), one callee-vocabulary table per language that both
  `[neat.effects]` and grimble detectors are views over; `frob:effects` claims and
  `grimble:effect` attestations name atoms from it; state the namespace decision with H7.

### H11. CI007 and DK004 scan text inside regions U declares opaque, where "nothing is ever computed" (HIGH)

- Where: universal-model.md:88-92 ("Every query returns Unknown or NotApplicable on it; nothing
  is ever computed through it"), :352 (shell word splitting: "the region is opaque");
  cicd.md:83-85 (`run:` bodies are shell regions "with string-code opaqueness"), cicd.md:121
  (CI007 scans `run:` for `${{ github.event.* }}`), cicd.md:133 (DK004 "shell region scan,
  May"); notes/research/lint-requirements.md:163-167 (consequence 5: "scanned set" for lexical
  rules).
- What: the two highest-impact CI/DK rules are text predicates over an opaque payload. U's
  query interface has `text and size` (:368-372) but does not say whether text queries see an
  opaque payload.
- Failure: an implementer following U 2.2 returns Unknown for every `run:` region, so CI007
  never fires (and with H5 unfixed reads clean), the 18 injection-vulnerable repositories in
  the survey pass.
- Fix: in universal-model.md 2.2 item 4 add: "`text`, `literals` and `prose` queries read
  the opaque payload's bytes (lexical facts are exact); only structural and binding queries
  return Unknown". Make the lexical exception explicit in the 47-query list (section 5).

### H12. The capability matrix's `n/a` survives in two files and 9.6 still has no not-applicable cell (HIGH)

- Where: code-model.md:117, :122, :284, :290 (`n/a`, `NotApplicable(reason)` = no detector,
  one Unresolved per node); grimble-model.md:143-147 (section 4: "reports that cell as `n/a`")
  versus grimble-model.md:279-291 (9.6: "`n/a` is retired", cells uses/undeclared/
  declared-unused/excused/unknown); notes/review/grimble-review.md:201-253 (H4 required
  `not-applicable(reason)`, `unmeasured(language)` and `unknown-by-design(reason)` cells and a
  detector row schema).
- What: the owner asked that the grimble system be thought out end to end; 9.6 fixes "no
  detector reads clean" but drops the review's not-applicable cell, so a CSS-only node carries a
  permanent Unresolved for `exec`, `net.connect`, `fs.write` (review H4 failure scenario, second
  half). The detector registry row schema, the crate that owns it, and the `detectors(lang, atom)`
  query are unspecified.
- Fix: replace code-model.md section 7's cell table with a pointer to grimble-model 9.6; delete
  grimble-model.md:143-147's `n/a` sentence; add to 9.6 a `not-applicable(reason)` cell declared
  by the adapter (clean) distinct from `unknown`; copy the review's detector row schema into 9.6
  and name the crate (same decision as H10).

---

## MEDIUM

### M1. Symref grammar generalization lives only in U; code-model.md 2 and migration.md promise "unchanged"

- Where: code-model.md:30-38; migration.md:36 ("Symref grammar unchanged"); universal-model.md:145-156
  (`<locator>::<Qual>.<Name>`, `path#cell=A1`, positional index for anonymous units).
- What: no syntax for the anonymous-unit index (bracket? `@`? `#`?); `#` is already the markdown
  slug separator; multi-part units sharing one symref conflicts with code-model.md:53-54
  ("ambiguity is an error"). Open question 2 (U :524-527) gates leases and acks but is not listed
  as blocking.
- Fix: move the grammar to code-model.md 2 as an EBNF covering locators, roles and anonymous
  indexes; state multi-part units resolve to one identity (not ambiguity); amend migration.md:36 to
  "file-based symrefs unchanged; new locator forms are additive".

### M2. D58 typed lock entries versus landed gob-lock and frob-ack

- Where: grimble-model.md:232-236; crates/gob-lock/src/file.rs:61-112 (entries keyed by symref
  string, fields sig/body/doc/targets); crates/gob-lock/src/lib.rs:8-10 ("callers decide what to
  acknowledge"; the ack planner is in frob-ack); boundaries.md:61 (gob-lock owns "the shared `ack`
  implementation").
- What: 9.2 does not say whether frob.lock adopts roles and flow keys or only grimble.lock does,
  nor that the ack planner moves from frob-ack to gob-lock (review M7, ticket G05).
- Fix: in 9.2 state "gob-lock gains `kind = symbol | flow`, `digest_scheme`, optional `attr`
  facet; frob.lock uses `symbol` entries only; the ack planner moves to gob-lock (G05)"; bump
  LOCK_VERSION with a reader for version 1.

### M3. SYS006 across languages is still unrepresentable: `norm_sig` is not a facet

- Where: grimble-model.md:232-236 (fields "the facet digests"), :310-311 (`norm_sig` in the adapter
  contract); code-model.md:78-79 (`Sig` "never used for digests"); universal-model.md:381 (norm_sig
  as a digest query); grimble-review.md:107-113, :139-147.
- What: a TS producer and Rust consumer of one contract have different facet digests by
  construction; equality is only meaningful over the normalized signature, which 9.2 does not
  store.
- Fix: in 9.2 add `norm_sig` to flow entries (`contract_sig_norm`, `producer_sig_norm`,
  `consumer_sig_norm`) per the review; delete code-model.md:78-79's "never used for digests".

### M4. Config inventory lacks every new knob

- Where: architecture.md:182-254. Missing: `[compute] public_signatures` and the other six 4.6
  rows (universal-model.md:341-352, only one key named); `[neat]` max_params, max_depth,
  raw_loop_statements, hook_statements, require_effects (neatness.md:86, :92-107, :126);
  `[neat.effects]` (neatness.md:69-71); `[ci]` allow_tag_pins_for, max_timeout, contexts,
  max_age_days, registry vocabulary (cicd.md:110-129); `[check] require_siblings`
  (grimble-model.md:274-275); expansion step budget (U :349).
- Fix: add rows with product file, materialized flag, default and owning crate after H7/H10;
  name every `[compute]` key in universal-model.md 4.6.

### M5. `[compute]` is a substrate knob in per-product files; frob and grimble can disagree

- Where: universal-model.md:341-343; architecture.md:168-170 (one config file per product).
- What: frob.toml `[compute] public_signatures = "required"` and grimble.toml unset yield two
  U terms for the same file (opaque in one, not the other); `frob check` merges both.
- Fix: put `[compute]` in one place (frob.toml read by every product, or a shared
  `compute.toml`), or require sibling JSON to carry the compute digest and refuse a mismatch.

### M6. `[gates.severity]` is reintroduced by cicd.md after rules.md removed it

- Where: cicd.md:109-110; rules.md:10-12 ("There is no 580-line `[gates.severity]` table");
  migration.md:16 (v1 table collapsed into `[rules.<id>]`); architecture.md:247.
- Fix: cicd.md:110 should say `[rules.<id>] severity`.

### M7. New directives are absent from code-model.md 4 and the gob-directives milestone split

- Where: neatness.md:61-68 (`frob:effects`, `frob:pure`, `frob:honest`, `frob:core`,
  `frob:shell`, `frob:hook [kind]`, `frob:dispatcher`, `frob:idempotent`, `frob:trusted`);
  universal-model.md:348 (`frob:calls <symref>...`); code-model.md:172-191 (verb list);
  crates/gob-directives/src/lib.rs:18-19 (milestone-1 verbs ticket, todo, doc, tests, invariant,
  accept, defer); grimble-model.md:115 (no `grimble:binds` in the table) versus :215 and
  code-model.md:239.
- What: no surfaces, target types or milestone; `frob:idempotent` "needs bound evidence" with no
  evidence kind; namespace depends on H7.
- Fix: add the verbs to code-model.md 4 with surface and target, mark them milestone 2, define
  what evidence discharges `frob:idempotent` (or drop it per neatness.md:34 "idempotence without
  evidence" not lintable), add `grimble:binds` to grimble-model.md:115.

### M8. CLI verb table is behind the new documents

- Where: cli.md:151-204. Missing: `grimble doctor`, `grimble fmt`, `grimble exceptions`
  (grimble-model.md:299-301), `frob init --ci` (cicd.md:154-157, open), `frob audit --online`
  (notes/research/cicd-survey.md:1015-1016). cli.md:154 marks `doctor [--languages]` milestone 1,
  but crates/frob/src/doctor.rs:18-26 has no `--languages`, and U :207-209, :514-515 redefine it as
  fidelity plus precision (milestone 2) while code-model.md:123-124 says it prints the
  Implemented/NotApplicable/Gap matrix. cli.md:200 lists `grimble vet` while the review cut defers
  grimble-vet (grimble-review.md:826-829) and 9.7's verb list omits it.
- Fix: add rows; change `--languages` to milestone 2 with U's semantics; resolve vet's milestone.

### M9. No single milestone-2 statement; milestone-1 status is stale

- Where: README.md:103 (D36), README.md:122 (D55); build-test-ci.md:19-25 and monorepo.md:89-92
  ("`frob-check`, `frob-land` and the self-host switch remain") although crates/frob-check and
  crates/frob-land landed (commits 45a93a68b, 683d91bcc) and notes/coordinator.md status log says
  T-0025 is complete on an unmerged branch; universal-model.md:500 (gob-ir first),
  grimble-model.md:301-304 (19 tickets, critical path), cicd.md:144-147 (adapters after gob-ir,
  tool bindings earlier), neatness.md:126-129 (require_effects "from milestone 2"),
  notes/coordinator.md "Milestone 2 backlog".
- Fix: add one "Milestone 2" section to build-test-ci.md (or a D-row) ordering T-IR, G7-G9 digest
  scheme, sibling contract, grimble cut, NEAT first ten, CI bindings then adapters; update the
  status lists to name frob-check and frob-land as landed and the self-host switch as pending.

### M10. The grimble milestone-2 cut and several design contracts live only in evidence notes

- Where: grimble-model.md:301-304 points at notes/review/grimble-review.md:797-833 for the 19
  tickets; the 47 query signatures (lint-requirements.md section 4) and the full polarity table
  with Pn min/max and Pc rules (:157-186); the detector row schema (grimble-review.md:249-252);
  the sibling JSON fields (grimble-review.md:187-199); CI predicates and default severities
  (cicd-survey.md:968-1002); the 37-rule NEAT table (notes/research/neatness.md section 7).
- Fix: copy each contract into its design file (U section 5 appendix, rules.md, grimble-model 9.5
  and 9.6, cicd.md 5, neatness.md 4) and leave the notes as evidence.

### M11. cicd.md disagrees with its own evidence on ids and rules

- Where: cicd.md:131-132 (DK002 no-latest, DK003 digest-pinned) versus cicd-survey.md:999-1000
  (DK002 base-pinned, DK003 no-latest); cicd.md:129 (CI015 "pinned SHA behind latest release")
  versus cicd-survey.md:996 (CI015 archived or Node-EOL actions); cicd.md:100 (GHA F4) versus
  cicd-survey.md:1009 (F3); cicd-survey severities "note" (no such v2 severity); cicd.md:107-108
  cites "section 8" of the survey, whose rule table is 9.3; cicd.md:116 (CI002 every workflow)
  versus survey :989 (top-level or every job).
- Fix: pick one numbering before any id ships (ids are permanent, D32), align CI015, map "note"
  to Advisory, fix the section pointer.

### M12. Tool-bound findings: no id mapping in the pipeline, and native suppressions bypass exceptions

- Where: cicd.md:51-60, neatness.md:111-116 (tool findings "under the NEAT id"); rules.md:213-217;
  crates/frob-check/src/tools.rs:21-60 (one TOOL001 per stage, no parser); cicd-survey.md:1011-1014
  (`source_rule` mapping); exceptions.md:12-17 (one primitive for all suppression).
- What: no design file defines the tool-id to frob-id map or `source_rule` on Finding; and a
  `#[allow(clippy::too_many_arguments)]` or `# zizmor: ignore[...]` hides the finding before frob
  sees it, with no kind, reason or exit.
- Fix: rules.md 4: tool stage gains `parser` and an id map, Finding gains `source_rule`; add an
  EXC rule (or a NEAT/CI meta-rule) that flags native suppressions of bound rules without a
  matching frob exception.

### M13. Crate ownership: gob-check, gob-pattern and the atom registry are in no crate list

- Where: grimble-model.md:295-299 (gob-check, "exception matching moves into gob-rules");
  grimble-review.md:822 (gob-pattern); architecture.md:14-25, :32-33 (`grimble-check` for
  bundle); boundaries.md:42-66, :105, :270-273 (counts); rules.md:298;
  crates/frob-obligations/src/lib.rs:192 (`apply_exceptions` lives in frob, while boundaries.md:53
  already claims gob-rules owns matching).
- Fix: add gob-check, gob-pattern and the registry crate to boundaries 2.1 and architecture 1,
  restate `bundle` in terms of gob-check, recount crates, and note the current home of
  apply_exceptions as the thing G06 moves.

### M14. U locations are not byte offsets, but Finding and FindingRecord are

- Where: universal-model.md:135-143; crates/gob-diagnostics/src/record.rs:11-31 (file, line,
  column only); gob-text TextRange spans (boundaries.md:46); cicd.md:81 and cicd-survey.md:1011-1014
  (YAML routes as pointer locations).
- Fix: list in universal-model.md 8 the gob-text, gob-rules and gob-diagnostics changes
  (`Location` enum with text, pointer, grid, graph variants; FindingRecord `location` object) and
  the SARIF logical-location mapping.

### M15. Edge-status vocabulary differs three ways, and landed scoping drops Unknown edges

- Where: code-model.md:255-258 (`Certain | ImportVerified | NameOnly`); crates/gob-symbols/src/graph.rs:37-56
  (`Resolved | Ambiguous | Unresolved`); universal-model.md:84-87 (`Must | May | Unknown`);
  crates/frob-check/src/scope.rs:34-42 (`CallEdge::Unresolved { .. } => {}`);
  crates/frob-tests/src/reach.rs:1-9 (ambiguous names fall back); rules.md:186-191, cli.md:137-140
  (`--ticket` dependents), build-test-ci.md:117-125 (touched-set selection).
- What: `check --ticket` and `frob test` silently under-approximate dependents when a call is
  Unknown; no design text says the selection is a lower bound or that it reports Unresolved.
- Failure: a ticket changes a trait method reached only through dynamic dispatch; the dependent
  file is outside the scoped run and its test is not selected; evidence records Passed.
- Fix: one vocabulary (U's) in code-model.md 6 with the mapping of landed variants; state in
  rules.md 4 and build-test-ci.md that an Unknown edge out of a touched symbol yields one
  Unresolved ("selection incomplete: N unresolved call sites") and widens to the file's crate.

### M16. Exceptions: STALE and prune are unsafe under Unresolved outcomes

- Where: exceptions.md:102-106 (STALE "unknown is not stale" covers cache and `--only`, not
  Unresolved); lint-requirements.md:175-178 (stale check needs per-rule Unresolved sites);
  universal-model.md:354-357.
- Failure: a file gains a parse error (a `hole`) around a site carrying `frob:accept INV002`;
  INV002 reports nothing there, EXC013 marks the accept STALE and `exceptions prune` deletes it;
  the next clean parse brings the finding back with no exception.
- Fix: exceptions.md 3: "a site where the rule's outcome was Unresolved (opaque, hole, May) is not
  stale"; require the rule outcome to carry its Unresolved sites (H6).

### M17. Can an exception suppress an Unresolved finding?

- Where: exceptions.md:12-24 (silent on severity); universal-model.md:336-339 (annotation-required
  must be loud); neatness.md:77-80.
- What: if `accept NEAT011 because=...` suppresses the annotate-or-opaque Unresolved, the loud
  failure is silenced without the declaration; if not, there is no way to park it.
- Fix: decide: Unresolved findings accept only `defer` (with ticket) and `baseline`, never
  `accept`; state it in exceptions.md 1 and add an EXC id.

### M18. EXC ownership numbers disagree

- Where: boundaries.md:138-139 (EXC005 and EXC007 ticket-bound in frob-obligations; EXC003 in
  gob-rules list) versus exceptions.md:149-151 and README.md:112 (D45: EXC003 and EXC007 are
  ticket-bound; EXC005 is the accept digest check); rules.md:285-290; exceptions.md:21 (REATTEST
  digest stored in `exceptions.toml`) versus :150 (digest in `frob.lock`).
- Fix: boundaries.md:138-139 to D45 numbering; one REATTEST source of truth.

### M19. U's "Exact only" for P0/Pn/Pc is stricter than the evidence and makes CYCLE and NEAT Pn rules mostly Unresolved

- Where: universal-model.md:239-240; lint-requirements.md:162-164 (Pn and Pc decide on bounds:
  max-type fires on `lo > N`, Pc fires on a path inside `lo` edges); grimble-review.md:815 (CYCLE Pc);
  neatness.md:90-107 (NEAT001/002/004/006/030 Pn).
- Failure: one May edge anywhere in a crate makes CYCLE Unresolved even when a Must-edge cycle
  exists; a 400-line function with one unexpanded macro is Unresolved for NEAT001.
- Fix: adopt the research table's bound rules for Pn and Pc in U 4.2 and keep Exact-only for P0.

### M20. grimble-model 9.4 gives CAP-STALE polarity P0; the research and its meaning are P-

- Where: grimble-model.md:257-258; lint-requirements.md:116 (CAP002 P-); grimble-model.md:129
  ("grant never observed"). Also only three SYS/CAP ids get a polarity (review H1(c) asked for all).
- Fix: CAP002 is P- (fires iff hi lacks a use); add a polarity column to the drift table at
  grimble-model.md:123-136; tie `grimble shrink` to Exact absence.

### M21. PM026 (public-surface change) is silent on languages without a public-API answer

- Where: pm-enforcement.md:87 (detected from the gob-symbols public-API graph and generated
  command/config metadata); universal-model.md:287 (`visibility` may be Unknown), :492-494 (G10
  re-exports ignored).
- Failure: a chore changes a re-exported Rust function or a Python module's public function
  (no adapter): PM026 does not fire and the chore lands without a user story.
- Fix: state PM026's polarity (P+) and that an Unknown surface in the diff yields Unresolved on
  the ticket's close guard.

### M22. README decision log: D56-D60 are recorded as decisions while their files are drafts, and the precedence rule omits the new files

- Where: README.md:4-7 (precedence: D23 onward win over every file); README.md:123-127 (D56-D60);
  neatness.md:120 ("proposed decision-log rows"); universal-model.md:3 ("for owner review").
- What: a reader applying README precedence treats U, NEAT and CI/DK as overriding code-model,
  rules and boundaries today. Rows D4 ("a structural IR"), D31 (H2), D42 ("audit M26 answered"
  versus M23), D43 (H8), D44 (directives must start a comment line; U :495-496), D49 (facet
  count), D55 (M9) are made false or partial by D56-D60 without a note.
- Fix: mark D56-D60 "PROPOSED" until accepted; add one row listing the D1-D55 rows each
  supersedes; add universal-model.md, neatness.md and cicd.md to the precedence sentence.

### M23. ast-grep status: "answered" in D42, "pending spike" everywhere else

- Where: README.md:109 (D42 "ast-grep-core 0.45.3 is compatible (audit M26 answered)");
  architecture.md:293; code-model.md:220-224 and rules.md:162-165, :312-313 ("pending a spike");
  notes/coordinator.md milestone-2 backlog ("ast-grep tree-sitter unification spike (M26)");
  grimble-review.md:822 (G17 blocked by the spike).
- What: version compatibility is answered; the second half (an adapter for its `Doc` trait) is
  now against U, not IrKind, and is not stated anywhere.
- Fix: say once (rules.md 3): "version: answered (D42); remaining spike: ast-grep `Doc` over U
  terms, blocks level-2 rules (G17)".

### M24. Parse-artifact cache keys omit the inputs that now change U terms

- Where: code-model.md:298-303 and architecture.md:58-62 (key: content blake3, adapter id,
  grammar version, schema version); universal-model.md:341-352 (`[compute]` decides opaque vs
  not), :349 (expansion budget); U scope graph is cross-artifact (:82-87).
- Failure: a repository flips `[compute] public_signatures` to `required`; cached artifacts keep
  the old answers and NEAT/COV rules evaluate stale terms until `.frob/` is deleted.
- Fix: add a compute-config digest to the parse key, and state that the scope graph is a repo-scope
  artifact keyed by the graph digest.

---

## LOW

### L1. grimble-model.md 9.8 says the identity change is "to be written into universal-model.md 2.2"

- Where: grimble-model.md:308-309 versus universal-model.md:75-81 (already written).
- Fix: "done in universal-model.md 2.2".

### L2. G9 is a decision left inside a gap list

- Where: universal-model.md:485-487 ("Decide: section-local body plus a separate subtree digest");
  not in U section 9 open questions.
- Fix: list it as open question 5, blocking the digest-scheme D-row (H8).

### L3. U 2.4 calls "sort inside a loop" a POL rule

- Where: universal-model.md:130-133; rules.md:116, boundaries.md:136, :147 (POL is tickets/docs;
  code policy is GPOL, universal structural rules are grimble-lints).
- Fix: "the universal structural rules of grimble-lints".

### L4. "excused" described as "grant waived"

- Where: grimble-model.md:283 versus :69 and code-model.md:283 (`excuses` is an explicit
  exclusion, no grant).
- Fix: "excused (atom explicitly excluded with a reason)".

### L5. `.grmb` exception examples spell the reason `reason`, not `because`

- Where: grimble-model.md:58 (`defer ... reason "..."`), :34 and :80-81; README.md:111 (D44: all
  four exception verbs spell the reason `because=`); exceptions.md:61-62.
- Fix: use `because` in the .grmb grammar (G01) and the example.

### L6. v1 `frob:waive` comments and generator output will fail the v2 self-check

- Where: rules.md:88, documentation.md:18, :58-69, :92 (`<!-- frob:waive DOC006 -->`);
  crates/gob-dev/src/render/rules.rs:92 (generated pages emit `frob:waive DOC004`);
  crates/gob-directives/src/rules.rs:30-33 (DSL001 unknown verb, Error); notes/coordinator.md
  (DSL001 on v1 waive comments is on the T-0025 cleanup list).
- Fix: at the self-host switch, emit `frob:accept DOC004 because="..."` from gob-dev and convert
  the design-file comments; until then note it in build-test-ci.md status.

### L7. Terminology drift: Unresolved, Unknown, Unmeasured, UNKNOWN, Unresolved-exit

- Where: grimble-model.md:219-220 (binding "Unknown, reported as SYS-UNRESOLVED": a rule alias,
  not the Unresolved severity); code-model.md:250-251 ("REACHES rather than UNKNOWN");
  exceptions.md:39 and boundaries.md:199 ("Unresolved-exit") versus grimble-review "UnresolvedExit";
  tickets.md:388-389 (Unmeasured evidence).
- Fix: one glossary row in universal-model.md 4.1: Unknown = query answer, Unresolved = finding
  severity, Unmeasured = evidence verdict; rename SYS001's alias to SYS-EMPTY-SELECTOR.

### L8. Repository CI contradicts build-test-ci.md and the CI rules it is to adopt first

- Where: build-test-ci.md:100-101 ("Every third-party action pinned by SHA");
  .github/workflows/ci.yml (`actions/checkout@v4`, `Swatinem/rust-cache@v2`,
  `taiki-e/install-action@v2`, no `permissions`, no `timeout-minutes`); cicd.md:145-147.
- Fix: either pin and add permissions/timeouts (a ticket) or correct build-test-ci.md:100 to
  "target"; list zizmor and actionlint stages in the CI table.

### L9. Derive and enum names drift from code

- Where: rules.md:281 and boundaries.md:54 (`TicketField` derive) versus
  crates/frob-ledger/src/schema.rs:3-10 (`TicketSchema`); documentation.md:63 (ticket schema
  "Milestone 2") although T-0028 landed the schema and docs/schemas has no ticket.json;
  rules.md:41-42 (`Lang(Python)`, `File | Graph | Repo`) versus crates/gob-rules/src/meta.rs:21-36
  (`Lang`, `File | Repo`); documentation.md 3 has no row for docs/schemas/sibling.json
  (grimble-model.md:266-267) or a languages/fidelity page from `doctor --languages`.
- Fix: rename in the docs, add the sibling.json, ticket.json and fidelity-page rows to the one
  path table, and a polarity row to the rule-page spec.

---

## Which file is authoritative for each topic (after the fixes above)

| Topic | Authoritative file | Others must point, not restate |
|---|---|---|
| Structural model / IR (Sigma_U, adapters, fidelity) | universal-model.md 2-3 | code-model.md 3 and 5, rules.md 2-3, boundaries.md gob-ir row |
| Identity and symref grammar | code-model.md 2 (absorbing U 2.6), identity notion from universal-model.md 2.2 | grimble-model.md 9.2, migration.md 3 |
| Digests and lock format | universal-model.md 7 for the scheme; code-model.md 2 for lock mechanics (digest_scheme, typed entries) | grimble-model.md 9.2, D43 (superseded), gob-lock rustdoc |
| Answer lattice, polarity, subject accounting | universal-model.md 4.1-4.2 | rules.md 1-2, lint-requirements.md 3 (evidence) |
| Severity lattice and gate/exit behaviour (Unresolved failing) | cli.md 2 (exit table) plus rules.md 1 and 4 step 8 | grimble-model.md 9.5, boundaries.md 1 and 6, products.md 6 |
| Rule metadata (derive fields, pages) | rules.md 2 | documentation.md 3 (page spec), neatness.md 4, cicd.md 5 |
| Rule families and owning crates | boundaries.md 2.5 (needs NEAT, CI, DK, CHECK rows) | rules.md 3 and 8, neatness.md, cicd.md 6, products.md 4 |
| Config inventory | architecture.md 6 | universal-model.md 4.6, neatness.md, cicd.md, grimble-model.md 9.5 |
| Directives (verbs, namespaces, milestones) | code-model.md 4 | neatness.md 3, universal-model.md 4.6, grimble-model.md 4 and 9.1 |
| CLI verbs and exit codes | cli.md 2 and 4 | grimble-model.md 9.7, cicd.md 7 |
| Capability matrix cells and atom registry | grimble-model.md 9.6 | code-model.md 7, universal-model.md 8 |
| Milestones | build-test-ci.md (Milestone 1 and a new Milestone 2 section) plus README D36 | monorepo.md 5, grimble-model.md 9.7, universal-model.md 8, cicd.md 6 |
| Generated pages and schemas | documentation.md 3 | build-test-ci.md 3 |

---

## Notes

Checked and found consistent (no finding):

- tree-sitter 0.27.0 and grammar pins agree across architecture.md:293, README D42 and every
  crate manifest (gob-languages, gob-directives, gob-symbols Cargo.toml).
- Rule id grammar (crates/gob-rules/src/id.rs:43-49, 2-6 uppercase letters plus 3 digits) accepts
  NEAT, CI and DK; no collision with frob, grimble or crunk families (boundaries.md 2.5,
  notes/crunk.md families). The only semantic overlaps are v1 VET009 "GitHub Action pinned to
  mutable ref" (notes/v1/gates-and-rules.md:463, KEEP into grimble-vet) with CI001, and
  grimble-arch's size/nesting metrics (boundaries.md:101) with NEAT001/NEAT004; both resolve once
  H7 decides ownership (mention them in the D-row).
- D56's "thirteen-operator signature" matches U 2.3's table; D58's summary matches section 9.
- D28's core (grimble never reads frob.lock or tickets; frob reads grimble only through `--json`)
  is still stated identically in products.md, boundaries.md, exceptions.md, grimble-model.md 7,
  code-model.md 6; H9 is the one place 9.3 strains it.
- The ticket-bound exception evaluation boundary (exceptions.md 1, boundaries.md 3.2,
  grimble-model.md 7) is consistent with 9.5's opaque `ticket=` field.
- cicd.md's "what a repository cannot show" correctly reports Unresolved by construction, and
  CI014/CI015 offline behaviour is Unresolved, satisfying the owner's fail-loudly requirement.
- neatness.md's unverified-claim rule (Unresolved, never clean) matches U 4.5-4.6.

Deliberately skipped or skimmed:

- tickets.md, pm-enforcement.md, gui.md and git-io.md were grepped for IR, digest, Unresolved,
  grimble and spawn content rather than read in full; their ticket-model content is unaffected
  by D56-D60 except PM026 (M21) and the spawn table (zizmor/actionlint/hadolint are new
  `[[check.tool]]` spawns; git-io.md:71 should list them when M12 lands).
- notes/research/paradigms.md, calculi.md and reading-list.md were not audited; the `[verify]`
  citations U open question 4 names remain unchecked.
- grimble-review.md MEDIUM and LOW items were read by heading only; this audit re-raised only
  those that section 9 touched (M3, M20) or that an older file now contradicts.
- No code was compiled or run; landed behaviour is inferred from source.
