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
