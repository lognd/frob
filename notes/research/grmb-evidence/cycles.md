# grmb audit/fix cycles

One section per audit/fix cycle of ticket ~MHGA5VN, appended, never one
file per cycle. Each cycle names the audit it answers, what was fixed
(with the decision and evidence rows), what was deferred (with reason and
a follow-up ticket), what was rejected by evidence, and what the next
audit should look at. Evidence rows (E, U) are in [evidence.md](evidence.md).

## Cycle 1 (2026-10-31)

Inputs: the fable cohesion audit of 2026-10-31 (findings C1-C15, the
syntax tables 2.1-2.5, splits S1-S5, merges M1-M9, reshapings R1-R12,
docs sprawl DOC1-DOC8) and the evidence review of the same day (54
sources, 53 verified; 8 doc contradictions; the pipeline verdict), both
against commit 577c8e00c2. The audit itself was a scratch file and is not
kept; its finding ids are cited here and in decisions.toml.

### Fixed

| Finding | Fix | Decision | Evidence |
|---|---|---|---|
| R1, M1, C2 (four evidence spellings) | one `verified_by` clause on every verifiable entity, `verified_by manual because=`; `evidence tests`, `evidence ref`, the test vmodel are deprecated (MDL012) | D150 | E24, E30 |
| R3, M2, C4 (rung named twice, three `status` keys) | `covered` everywhere; JSON `design_status`, `design_status_hi`; overlay verdicts aligned with SysML | D151 | E25, E28 |
| R5, R9 (`:` half), S2, C8, C9, table 2.1 `->` row, 2.4 terminator and layout rows, doc contradiction 4 | `->` follows only; `=>` arms and outcome-map entries left to right; `:` step outcome type; waypoint chain is a statement list; `via FLOW` dropped from hops | D152 | E39, E24, E26, E27 |
| R8, M8, 2.2 retry row, doc contradiction 8, GAPS G3 | one `retry [S] max N [within T] [else ...]` grammar; default target; default `else` never spelled | D153 | E34, E45, E50, U2 |
| pipeline verdict | no `$` placeholder | D154 | E44, E45, E47, E50 |
| doc contradictions 1-3, table 2.3 | one keyword table with classes, every rev 2 word, `r#` escape, `chain` a planning word, pack kinds may not equal planning words, `outcome` dropped | D155 | E2-E4, E18-E21, E24, E27, E32 |
| S3, table 2.1 `include` row | file include is `use`; `include` is scenario invocation only | D156 | E24 |
| R2, S1, C1 (whole corpus MDL031), table 2.1 `system` row | file membership by `system NAME;` or one top-level braced system; `system.X` is the one remaining sense | D157 | U1 (no outside evidence) |
| R4, M3, C7 | `budget` folded into `claim bound` with planning targets; PLAN024/025 retired | D158 | U4 (no outside evidence) |
| R10, M5, table 2.2 label row | `///` replaces `title` | D159 | none (internal) |
| R11, M4, S5, C11, table 2.2 debt and ticket rows | one debt key set; `review=` becomes `until=`; `ticket=` a string everywhere; `owner=` kept (R11 adjusted, not dropped) | D160 | none (internal) |
| R12, S4, M6, C13, tables 2.2/2.5 rows (`because`, `renamed_from`, two-word, `cli`, `sorry` body, `verified_by` on system, `node`/`in node`) | `on page`, actor `in node`, `because=` canonical, ident-only `renamed_from`, `cli` core kind, whole-body `sorry`, no `verified_by` on system, two-word rule | D161 | E40, E41 |
| doc contradiction 6 | `one_of` rolls up with the join | D162 | E29 |
| doc contradiction 7 | scenario is use-case level, arm path is a Gherkin Scenario; mapping table 11.10 | D163 | E22, E23 |
| R7 (applied part), C5 | derived V-model edges and graph JSON use the surface words | D164 | E24, E30 |
| C3 (pairing stated twice) | one derived pairing table (13.3) with flow, contract and waypoint rows; the informal rev 2 paragraph removed | D164 | E24 |
| 2.4 impl-node row | the impl node is the first waypoint's node | D152 | none (internal) |
| 2.5 corpus rows | timer `attr period`, `non_goal` in the system body, `one_of` inside a goal block, f03 header `fails with`, f12 ident rename, f13/f15 predicted MDL006 (not MDL031), d01 `_ => unknown` on a closed set removed | D157-D161 | U3 |
| DOC1 | decision text in decisions.toml (full text replaces the truncated summaries for D65-D77, D124-D149); spec headings are one-line anchors; the README D139-D149 table deleted | D165 | - |
| DOC2 | grimble-model.md section 2 (illustrative grammar, 69 lines) replaced by a pointer; spec 14.1 cross-check deleted | D165 | - |
| DOC3, DOC4 | grmb-planning.md merged into grmb-spec.md and deleted; section 0 (R1 disposition) and 16.1 (brief changes) dropped as history, retrievable at `577c8e00c2:docs/design/grmb-planning.md`; one grammar (11.1) | D165 | - |
| DOC5 and the ERR collision | every rule table in grmb-spec.md 16; ERR002-ERR005 renumbered PLAN041-PLAN044; PLAN-G01..G10 renumbered PLAN050-PLAN059; PLAN040 given a row | D165 | - |
| DOC6 | the six raw R1 notes (6862 lines) deleted; evidence.md section 4 says where to retrieve them; the synthesis header points there | D165 | - |
| DOC7 | the spec keeps one example (18.2, both layers); the long web_app, thermostat and repository examples are gone (the first two live on as crates/grimble-model/tests/corpus/plan/web_app and thermostat); GAPS.md folded into the spec's one open-questions list (19) and deleted | D165 | - |
| DOC8 | stale pointers in grmb-spec.md, grimble-model.md, docs/design/README.md, the corpus README and the synthesis fixed | D165 | - |

Docs line counts (docs/design grmb-bearing files):

| File | Before | After |
|---|---|---|
| docs/design/grmb-spec.md | 1781 | 2912 |
| docs/design/grmb-planning.md | 1612 | deleted |
| docs/design/grimble-model.md | 423 | 360 |
| docs/design/README.md | 73 | 52 |
| notes/research/grmb-r1-{practice,failure,languages,incompleteness,graphs,ergonomics}.md | 6862 | deleted |
| notes/research/grmb-corpus/GAPS.md | 34 | deleted |
| notes/research/grmb-evidence/evidence.md, cycles.md | - | new (the two allowed files) |

### Deferred (with follow-up)

| Finding | Why deferred | Follow-up |
|---|---|---|
| parser and checker still read the rev 1 spellings | the planning layer is IMPLEMENTED in crates/grimble-model (P1: parse/plan.rs, plan_check.rs, keywords.rs, tests/corpus/plan), contrary to the corpus README's "no parser"; the crate was leased by ERF5VCQ. The spec keeps every old spelling legal with MDL012 until then. keywords.rs also lacks `attests` and `for`, which the spec reserves | ~03B2YRN (scope `crates/grimble-model/**`, `docs/reference/rules/**`; 8 points; acceptance: parser accepts every cycle 1 spelling with MDL012 on old ones, keywords.rs equals spec 2.6, MDL031 implements D157, corpus respelled, comment pointers fixed) |
| rules.md MDL range note (MDL001-MDL021 only), the PLAN/AMB ranges, ERR ownership; sibling-contract.md and sibling.json planning keys | files leased by ERF5VCQ; the renumbering was done on the grmb side as instructed | ~Q1GEE3D (scope `docs/design/rules.md`, `docs/design/sibling-contract.md`, `docs/schemas/sibling.json`; 2 points) |
| a real `citations` field in decisions.toml | gob-dev's `Decision` struct is `deny_unknown_fields`; cycle 1 wrote `# citations:` comment lines and a `see` link to evidence.md | ~2XRXGMP (scope `crates/gob-dev/src/render/decisions.rs`, `docs/decisions/**`; 2 points) |
| DOC4 length target (~2500 lines) | the merge reached 2912 lines while adding the keyword table, the one grammar, the debt key set, the evidence section and the open-questions list; the remaining bulk (frob join 17.2-17.6, document anchors 4.5.1, runner ids 4.5.3) belongs to docs outside this lease | ~2TSHHNP (scope `docs/design/grmb-spec.md`, `tickets.md`, `pm-enforcement.md`, `code-model.md`; 3 points) |
| M9 (block step declarations), C6 (the word "realization"), C10 (`flow condition`), C12 (two acceptance channels), C14 (three decision records), C15 (`module` vs `system`), table 2.1 rows `for`, `as`, `kind`, `page`; table 2.2 rows "has type/kind" and "precedence"; arm qualification depth (2.4) | no evidence either way and no owner request this cycle; each is in grmb-spec.md 19 (items 24-29) or listed below for the next audit | next audit |
| DOC7 `frob:todo` markers on stress fixtures | a marker needs the parser ticket id; folded into ~03B2YRN's corpus acceptance | ~03B2YRN |
| a separate notes/research/README.md index (DOC6) | notes/README.md already indexes notes/research/ one row per note; a second index would be the docs explosion the owner forbids, so the rows were added there instead | none |

### Rejected by evidence

| Audit item | Evidence | Outcome |
|---|---|---|
| R6 (drop `include` for scenario invocation) | E24: SysML v2 keeps `include` for use-case inclusion | the FILE include was renamed `use` instead (D156) |
| R7 verb trim (drop `satisfies`, `allocates`, `blocked_by`) | E24: SysML v2 keeps `satisfy`, `verify`, `allocate` as keywords | vmodel verbs unchanged; only the derived-edge naming was applied (D164) |
| R11 "an owner is whoever holds the ticket" (drop `owner=`) | no evidence for dropping; it loses information | `owner=` kept in the shared key set (D160) |
| a placeholder token (quartzite `$`) for grmb | E44 (no consensus, `$` blocked where it had a meaning), E45, E50 (placeholders only where values flow); grmb threads no value | rejected, default targets instead (D154) |

### Not changed (owner-fixed)

D139 tokens (`->`, `=>`, `-!>`, `*`, no `-?>`), `_`/`unknown`/`open`/
`closed`, `one_of [exclusive]`, `sorry`, actors and `external`,
SYS015/SYS016, derived V-levels, dotted names, `claim`/`proof`/`attests`,
goals as keyed variant sets. D139 is marked `amended` by D152 only for
its last sentence (`->` meaning "reaches" inside a chain).

### Suspected remaining for the next audit

1. `PLAN016` (scenario retry over a non-idempotent step, Warn) and
   `AMB002` (ambient retry, Error) judge one fact at two severities; the
   scopes were separated, not merged.
2. `MDL014` (unpaired `verifies`, Error) vs `PLAN050` (evidence scope vs
   paired level, Advisory) still differ in severity; justified as two
   facts (hand-written link vs classified test), worth a second look once
   the test vmodel is gone.
3. Three `level` scales remain in one JSON document (fidelity F0-F4, the
   V-model levels, the 0-4 "Level" column of grmb-spec 1.1).
4. `for` has three meanings (impl target, `verified_by ... for` arm
   selector, template `excuse ... for`), `as` two (mount prefix, goal
   dimension), `kind` three (node clause, vmodel clause, selector
   predicate), `page` two (entity, realization kind).
5. Arm-pair qualification has three depths (`v`, `step.v`,
   `owner.step.v`) between patterns, `verified_by ... for` and waypoint
   `for`.
6. `in node` on an impl is now redundant with the first waypoint's node
   when a chain exists (13.4); maybe drop it there.
7. The rule `system` marker plus braced body (11.2) has two ways to join a
   file to a system (mount and membership); D157 kept both.
8. The example (18.2) and the corpus were checked by eye only; the parser
   ticket must confirm every documented finding, in particular d03's
   ambient `retry` over a non-idempotent `system.charge` (AMB002 is not
   listed in d03's expected findings).
9. Decision records of other design docs (not grmb) still hold full text
   in their homes; DOC1 was applied to the grmb decisions only.
10. Stale pointers outside the lease: code comments in crates/grimble-model
    and docs/reference/rules/MDL028.md cite grmb-planning sections;
    notes/review/docs-consolidation-2026-10-31.md (a frozen review) cites
    the deleted files.
11. The `use` keyword was chosen from the evidence file's example; no
    source ranks `use` against `load`, `file` or Rust's `mod`.

## Cycle 2 (2026-10-31)

Input: the cycle 2 audit of head 774eb02bf3 (4 HIGH, 11 MEDIUM, 14 LOW;
a scratch file, not kept; its ids are cited here). Before fixing,
origin/experimental was merged (ERF5VCQ landed: grimble graph export with
planning rows, sibling-contract.md 3.8.1, sibling.json). Every finding was
fixed in place; none was deferred to a new ticket.

### Fixed

| Finding | Fix | Decision |
|---|---|---|
| H1 keyword table incomplete (`via`, `title`, `system`, markers) | `via` reserved; DEPRECATED class (`title`, `review`); `system` in item-head and planning-word classes; markers `outside` and `lang` only; "left with no bridge" lists only `budget`, `outcome`, waypoint `via` | D166 |
| H2 example FLOW002 and incomplete corpus predictions | 18.2 gains an `endorse` boundary and a complete per-rule findings list; every domain mockup's EXPECTED block rewritten as complete for MDL, FLOW, CLAIM, PLAN, SYS015-016, AMB, with IF EDITED lines for conditionals; d02 SYS015 now "Unresolved on two pairs"; d02 and d09 gain the boundary their trust step needed (and d02 a rate, FLOW003); d03 and d11 list the ambient-retry hazard, d11's arm PLAN016 removed (calls_tool is idempotent); d07 PLAN007 replaced by PLAN003, PLAN012, PLAN014; d09 PLAN001 view_report; P1 and P6 exits restated (one-way check; d02's two Unresolved pairs) | D168-D174 applied; no new decision for the lists |
| H3 mount vs marker | one precedence: the marker is a `ref` resolved from the mount prefix, never declares under a mount, is redundant or MDL031; production `system ref ";"`; 9.5 row; MDL031 row; the two cases written out in 11.2 (no new fixture file, to keep the corpus file set fixed) | D167 |
| H4 bridge breaks its own rule | one closed bridge list in 11.1 equal to what P1 read; waypoint `via`, `->` hops and `<-` maps are MDL000 (never parsed); `verified_by` on a system is bridged (ignored, MDL012); horizon "through major 2" stated in 3.4 for every layer; a written default retry target is valid, fmt-only | D168 |
| M1 PLAN016 vs AMB002 | PLAN016 covers arm and ambient retries; AMB002 retired | D169 |
| M2 MDL014 level pairing on the deprecated form | dropped; MDL012 message names the redundant `level`; PLAN050 judges both spellings | D170 |
| M3 duplicate evidence MDL014 and MDL017 | MDL017 only | D170 |
| M4 evidence resolving to nothing | ladder in 8.3: missing file `planned`, wrong id SYS011; PLAN005 condition updated | D171 |
| M5 three pair spellings | `pair = step_ref "." name`; 14.1 example `for customer.pays.declined`; anchors spell the pair the same way | D172 |
| M6 `_ => unknown` on a closed set in 14.1 | line removed | - |
| M7 PLAN001 on a satisfied `one_of` | exempted (PLAN001 and PLAN005); d10 records the absence | D173 |
| M8 impls-only vs MDL031 | PLAN013 PLAN-UNUSED-IMPL (Advisory) for `for *`; MDL031 only for a named target; f09, f10b updated | D174 |
| M9 no architecture grammar | 4.10 item grammar (file, header, items, body-less `;` forms) that 11.1 extends | D175 |
| M10 ambient per-class and node override | removed from the surface; policy body with `verified_by` (AMB008 was unsatisfiable without one, found while fixing); escalate semantics stated; AMB006 retired | D177 |
| M11 one word several meanings | 2.2 table rows for `for`, `kind`, `on`, `in`, `as`; goal dimension is `attr dimension = K;` (bridged `goal P as K`); `page` dropped from the realization vocabulary; corpus `goal X as K` removed | D176 |
| L1 `review=` in 9.2 | `until`; bridged `review=` maps to the same term | D160, D168 |
| L2 inverted U kind names | U kind names frozen (stated in 9.2) | D178 |
| L3 clause order says `evidence` | `verified_by` | - |
| L4 entity counts | 5.1 and 10.1 cover all kinds of sections 4 and 11 | - |
| L5 "three contexts" | two | - |
| L6 MDL006/MDL014 "not a vmodel" | aligned with 4.5 (vmodel or planning entity) | - |
| L7 `ticket=` opaque and shape-checked | grimble checks non-empty only; frob checks the ULID (DSL002) | D178 |
| L8 retry default under `unknown` | `_` or `unknown` needs an explicit `else` (12.5, MDL027) | D178 |
| L9 two `common`s | one `common` and `alias_etc` in 4.10; template uses `alias_etc` | D175 |
| L10 include wording in MDL002/003/019/020 | `use` (aliases keep their ids) | - |
| L11 duplicated level table | 1.1 column dropped, points to 13.3 | - |
| L12 garbled ambient sentence | rewritten | - |
| L13 overstated citations | D161 drops E41; D164 says E24 backs three of seven verbs; D151 says SysML's four plus `not-run`; evidence.md rows match; also restored audit ids C1/C2/C4 that cycle 1's U-renaming had turned into U1/U2/U4 in three evidence rows | - |
| L14 corpus nits | f01 `_ =>`; f03 states MDL032 and MDL022 as written; f07 lists PLAN010 and the conditional PLAN016, drops `system s;`; f13 two MDL006; d04 `topic` takes a name (grammar note in 14.1); README presumes steps too | D178 |
| stale outside the lease (audit note) | grmb-r2-verification.md L519 points to spec 13.3; grimble-model.md table rows (`verified_by`, no flow `via`) and Decisions header fixed (lease widened per file) | - |

### Not fixed in cycle 2, with existing tickets

- ~Q1GEE3D (rules.md, sibling-contract.md, sibling.json): now more
  urgent, because ERF5VCQ landed a graph export and sibling-contract.md
  3.8.1 that emit `status`, `status_hi` and the rung `verified`, which
  D151 renamed (`design_status`, `covered`). The shipped code and the spec
  now disagree; the fix touches crates/grimble graph code as well as the
  docs, so it is not trivial and stays with that ticket (its acceptance
  should be read as including the graph code).
- ~2TSHHNP (spec length): cycle 2 grew the spec to 3120 lines (item
  grammar, bridge list, findings list, keyword-meaning rows).
- ~03B2YRN (parser): must now also implement D166-D178 (bridge list,
  marker precedence, `pair`, PLAN013, ambient body).

### Suspected remaining for the next audit

1. The corpus EXPECTED lists were derived by reading; PLAN030-034 and
   PLAN041-042 are excluded because they depend on code.
2. SYS016 under unknown step nodes is argued "not reported (P-)" in 18.2;
   the P- reading of a flow-exercise rule over Unknown nodes deserves a
   check against binding.md's polarity text.
3. `attr dimension` inside a goal block makes `attr` the one non-variant
   clause in that block; check it does not collide with a variant named
   by an escaped `r#attr`.
4. The deprecated class holds `review`, an attribute key, although 2.6
   says attribute keys are never keywords; it is listed for completeness
   of the bridge, not as a word the lexer reserves.
5. 4.10 is a skeleton: `grant`, `value` and `clause` are referenced by
   prose, not productions.

## Cycle 3 (2026-10-31)

Input: the cycle 3 audit of head 8d857abf40 (2 HIGH, 8 MEDIUM, 11 LOW; a
scratch file, not kept). origin/experimental was merged first (already up
to date at that point). Every finding was fixed in place; one code move
is ticketed.

| Finding | Fix | Decision |
|---|---|---|
| H1 SYS016 silent over Unknown nodes | SYS016 Unresolved while an exercising step use or hop has an Unknown node (16.3); 18.2 and d02, d03, d04, d09 list it | D179 |
| H2 `sorry` is a U hole, so fmt refuses drafts and MDL goes Unresolved | `sorry` is `apply(kind=sorry)`, not a hole; 9.3 item 6 and the 16.1 preamble name `hole(kind=parse-error)` | D180 |
| M1 `page` used as a keyword outside item position | `page` also a planning word; 11.7 note | D181 |
| M2 ambient `retry` vs `restart` undefined | defined in 15.1: retry keeps state and repeats system steps (PLAN016), restart loses state (AMB009); d03 and d11 lists drop the actor steps | D182 |
| M3 chain-only impls never bound | `bound` and PLAN004 count waypoints; route/topic resolve on an adapter match; d01, d02, d04 list PLAN004 absent | D183 |
| M4 one untested pair, two obligations | one PLAN006 per pair, covering arms and map entries; evidence anywhere for the pair discharges it; PLAN043 retired; d01, d02 lists merged | D184 |
| M5 `sorry` in positions the grammar lacks | 15.3 cut to the three grammatical positions | D180 |
| M6 P1 exit needs findings P1 does not ship | exits split by family (P1 MDL, P2 PLAN001-014, P6 SYS015-016, P7 AMB/PLAN015-016/PLAN030-044); corpus README and headers match | - (milestone text) |
| M7 respelled clauses change U names against D178 | D178 scoped to KIND names; attr names follow the current word, one restamp with reason; `title` lands in Doc; export edges follow; added to ~03B2YRN's acceptance | D186 |
| M8 outcome.rs reports the opaque error set under PLAN011 | PLAN041 owns it (Error; Unresolved, required, on opaque, waypoint anchor); code move ticketed | D185; ticket ~YTCRAEM (scope `crates/grimble-bind/**`, `docs/reference/rules/**`; 2 points; acceptance: PLAN041 required Unresolved on the waypoint anchor, test asserts rule id and anchor) |
| L1 goal dimension in Sig | Attr facet | D186 |
| L2 `review` in a keyword class | class renamed "words and keys recognized only to report MDL012" | - |
| L3 `pair` ambiguity, no `unknown` anchor | last segment is the variant; `arm[OWNER.STEP.unknown]` | - |
| L4 `verified_by` on boundary | refused in the 4 table too | - |
| L5 PLAN007 affordances | `external` row; system steps of timer/device-triggered scenarios accept `isr`/`driver`; d02's PLAN007 line now "absent" | D181 |
| L6 corpus nits | f04 cites 9.6, f06 cites PLAN016, f10a lists PLAN005 | - |
| L7 D155 not amended | amended by D166 (also D178 by D186, D142 by D180, D147 by D182, D148 by D184/D185) | - |
| L8 notes/README ranges | D139-D178 / D150-D178 | - |
| L9 `use` inside bodies | top-level only (3.2, 4.10 `item - use`) | D181 |
| L10 route/topic name vs selector in flat realizations | `realization` takes `( selector | route )`, kind decides | D178 |
| L11 two `value`s | `attr_value` in 4.10 | D181 |

### Suspected remaining for the next audit

1. The one-time digest restamp of D186 assumes no lock records planning
   Body digests before the parser ticket; not verified against
   grimble.lock contents of real repositories.
2. "Triggered by a timer or device actor" (PLAN007) needs a definition for
   scenarios reached only through `include`.
3. Ambient `retry` repeating "every system step of every scenario it
   covers" may over-report PLAN016 for scenarios whose faulting step
   precedes the non-idempotent one.

## Cycle 4 (2026-10-31)

Input: the cycle 4 audit of head 1e9307a273 (1 HIGH, 3 MEDIUM, 7 LOW; a
scratch file, not kept). origin/experimental merged first (XCB72NG profile
fix). Every finding fixed in place; no new ticket.

| Finding | Fix | Decision |
|---|---|---|
| H1 PLAN014 single-variant set fires on 10 mockups | PLAN014 judges refinement sets only (goal block at a goal path, or `one_of`); an actor's set may have one variant (11.4, 16.2); corpus unchanged | D187 |
| M1 AMB004 undefined, d11 fires it | the R2 condition moved into 16.4; d11 lists AMB004 (product 6) | D188 |
| M2 PLAN ids outside every milestone | P2 ships PLAN001-005, 007-014, 017, 018, 020, 027 with a matching exit; P3 PLAN021, 022; P4 PLAN006 and PLAN050-059 with an exit | - (milestone text) |
| M3 whole-body `sorry` vs required clauses and obligations | it stands for the body: no MDL026/MDL031, `declared`, own PLAN003-006 suppressed for one PLAN015, includers see `Out = Unknown`; MDL026 row and f14 note it | D189 |
| L1 11.10 bridged goal spelling | `goal G { attr dimension = K; ... }` | - |
| L2 13.1/17.1 waypoints in B | waypoints add `realization` rows with their kind; JSON carries the waypoint name | D183 |
| L3 AMB003 dead | `max` and `else` optional in the production, AMB003 reports their absence | D190 |
| L4 PLAN015 "released entity" undefined | every `sorry` (Warn; Error under a release profile); 15.3 names PLAN015 | D190 |
| L5 trigger through `include` | 12.6: the trigger is the actor of the scenario's own first step through leading includes | D190 |
| L6 `unknown` as a PLAN006 pair | `_`/`unknown` arms are not coverage subjects (13.2); d04, d11 lists fixed | D190 |
| L7 bridged `verified_by` on system refused by the grammar | `sys_member` admits it with the bridge comment | D168 |

### Suspected remaining for the next audit

1. AMB004's "product" is reported per pair of layers; a three-layer stack
   (ambient over include over arm) is not specified.
2. A whole-body `sorry` scenario that realizes a goal: does that goal count
   as covered for PLAN001? 15.3 says the scenario is `declared`; coverage
   (12.2) reads `realizes` and would count it.

## Cycle 5 (2026-10-31)

Input: the cycle 5 audit of head c3333cc9d9 (0 HIGH, 7 MEDIUM, 8 LOW; a
scratch file, not kept). origin/experimental merged first (up to date).
Every finding fixed in place; no new ticket. Fixes were chosen to avoid
growing the spec (net +27 lines, most of it decision anchors).

| Finding | Fix | Decision |
|---|---|---|
| M1 `_` arm "not a coverage subject" | corrected: `unknown` none, `_` covers its pairs (13.2) | D191 |
| M2 AMB004 inheritance, faulting scenario, three layers | 15.1: the outermost scenario's policy handles a fault inside an include; AMB004 one finding per innermost retry with the product of every enclosing `max` | D192 |
| M3 PLAN017 cannot fire | retired into PLAN011 (detail names the `unknown` arm); 15.4, f02, d05 reworded | D193 |
| M4 PLAN011 in P2 | P2 drops PLAN011 (and the retired PLAN017); P7 ships PLAN011 and PLAN030-034 with the other code-fact rules; corpus headers list PLAN011 as code-dependent | D193 |
| M5 sorry-bodied scenario's header | header is not a hole: `realizes` covers (tainted), PLAN002/010/027 and MDL006 run; f14 gains `scenario refund ... sorry;` | D194 |
| M6 PLAN006 in the sorry-suppressed set | suppression per kind; PLAN003 and PLAN006 never suppressed; f14 lists PLAN006 and PLAN005 | D194 |
| M7 waypoints have no anchor | `wp[NAME]` / `wp[K]` in 9.4; 14.4 and 17.1 point at it (the ~YTCRAEM acceptance "waypoint anchor" now has a definition) | D195 |
| L1 MDL026 parenthesis | "does not fire this" | - |
| L2 `repeat` requires `max` despite its note | `max` optional in the production, MDL027 reports it; policy comment fixed | D190 |
| L3 `{ sorry; }`, empty-scenario PLAN014 | `{ sorry; }` is the whole-body form; PLAN014 drops "an empty scenario" (MDL026 owns it) | D194 |
| L4 13.3 `sorry` in `verified_by` | whole-body `sorry` stands in for the evidence | D194 |
| L5 README and P7 content | README lists the per-milestone ids; P7 content names its code-fact rules | D193 |
| L6 PLAN014 counting | "counting the variants inside its groups" | D187 |
| L7 unnamed waypoint in the JSON | JSON `waypoint` carries the `wp[..]` anchor | D195 |
| L8 Unknown trigger | PLAN007 and MDL029 Unresolved | D194 |
| (found while fixing) f02 had an `unknown` arm with the known `expired` unmatched (MDL032) | `expired` arm added | - |

### Suspected remaining for the next audit

1. D192 makes an included scenario's own `ambient` clause dead config when
   it is never triggered; no rule reports that dead clause.
2. `wp[K]` positions shift when a waypoint is inserted earlier in the
   chain, so a finding fingerprint on an unnamed waypoint is stable only
   until the chain is edited; requiring names (MDL008) was not chosen.

## Cycle 6 (2026-10-31)

Input: the cycle 6 audit of head fb6e342574 (0 HIGH, 3 MEDIUM, 6 LOW; a
scratch file, not kept). origin/experimental merged first (up to date).
Every term touched was grepped across the spec, corpus, decisions and
evidence before editing. All findings fixed in place, recorded as D196;
no new ticket. The spec shrank from 3235 to 3173 lines (the decision
anchors were compacted to two lines each).

| Finding | Fix | Decision |
|---|---|---|
| M1 AMB004 include arm reports amplification that D192 rules out | include arm dropped; AMB004 is per (arm retry, applying policy) | D196 |
| M2 product over alternative roots; "covers" undefined | one finding per distinct applying policy; 15.1 says which scenarios an ambient retry applies to | D196 |
| M3 `sorry` element untyped | 12.3: `Out(sorry) = Unknown`, no `Succ` pair, no step use; a `sorry` terminal adds Unknown to `E(s)`; 12.6: a leading `sorry` gives an Unknown trigger; f14 gains `scenario ship` | D196 |
| L1 `{ sorry; }` on impl/page; no U row | restricted to scenarios; encoded as the unit's only Body child (15.3, 9.5) | D196 |
| L2 16.1 "never a `sorry`" | the preamble names the Unknown type and trigger as the exceptions | D196 |
| L3 duplicate waypoint names | unique per chain, MDL008 (14.1 and the MDL008 row) | D196 |
| L4 `wp[K]` "stable" | stable under fmt only, renumbers like `clause-key[i]`; name waypoints that carry maps, evidence or findings | D196 |
| L5 two `_` pairs, identical records | PLAN006 detail names the pair (13.2, 16.2 row) | D196 |
| L6 PLAN040 in no milestone | P7 content | D196 |

D188, D191, D192, D194 and D195 are marked amended by D196.

### Suspected remaining for the next audit

1. A `sorry` terminal now makes `Out(include s)` Unknown; whether MDL023
   on the includer (unhandled collected pairs) is then Unresolved was not
   spelled out beyond "typing there is Unresolved".
2. AMB004 needs the set of triggered scenarios that reach an arm retry;
   the spec does not say whether a scenario reachable only through
   includes (never triggered) contributes a policy.

## Cycle 7 (2026-10-31)

Input: the cycle 7 audit of head ae3ee79a4f (0 HIGH, 1 MEDIUM, 4 LOW; a
scratch file, not kept). origin/experimental merged first (up to date).
Every touched term (`sorry` terminal, `E(s)`, `Out = Unknown`, triggered
scenario, whole-body form, `body(..)`) was grepped across the spec,
corpus, decisions and evidence first. All findings fixed in place as
D197; no new ticket; the spec stays at 3173 lines (14.3's table became a
paragraph and three history lines were folded to offset the additions).

| Finding | Fix | Decision |
|---|---|---|
| M1 `sorry` terminal vs a declared `fails with` | a declared `F(s)` bounds the hole (E(s) = F(s) stays exact); only an undeclared set, and `Eok`, become Unknown; 12.3, 12.4 and 15.3 say the same | D197 |
| L1 "triggered scenarios" undefined | every scenario is triggered; the policies applying to a scenario are its own override, else the system's, plus its transitive includers' overrides (15.1); PLAN016's wording follows | D197 |
| L2 rules reading pairs of an Unknown outcome | 12.3 names them: MDL022-025, PLAN006, PLAN016, AMB004 Unresolved at that subject; the set is Unknown as a whole | D197 |
| L3 `body(C)` gives `sorry` to actors, variants, steps | grammar restricted to scenario, impl, page; 15.3 says so | D197 |
| L4 `{ sorry; verified_by ..; }` | a main chain of one `sorry` terminal is the whole-body form whatever else the body holds; a chain with no element gives an Unknown trigger; 9.5 row reworded | D197 |

D189, D192 and D196 are marked amended by D197.

### Suspected remaining for the next audit

1. With a declared `fails with`, a whole-body `sorry` scenario types as
   `Eok + F(s)` with `Eok` Unknown; an includer's `=>` therefore still
   checks the `F(s)` arms exactly but the `ok` arm Unresolved; the
   mixed verdict per arm is implied, not stated.
