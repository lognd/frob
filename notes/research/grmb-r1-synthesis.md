# grmb R1 synthesis: what the evidence changes in grmb-planning.md

Ticket ~19SEHXJ (research cycle R1), coordinator synthesis, 2026-10-09.
ASCII only. Inputs, all read in full including each note's section 7
(verification pass), which supersedes earlier text in the same note:

| Key | Note | Topic |
|---|---|---|
| A | notes/research/grmb-r1-practice.md | design practice (design docs, RFCs, ADRs, use cases, modeling surveys) |
| B | notes/research/grmb-r1-failure.md | failure modes, erosion, conformance tools, distributed failures |
| C | notes/research/grmb-r1-languages.md | 30 design/requirements/spec languages and their fate |
| D | notes/research/grmb-r1-incompleteness.md | partial models, three-valued checking, holes, designer cognition |
| E | notes/research/grmb-r1-graphs.md | graph core, UML/MOF/EMF, Datalog, traceability, sum types |
| F | notes/research/grmb-r1-ergonomics.md | Rust/Zig/Swift/Elm ergonomics, diagnostics, annoyances |

Target: docs/design/grmb-planning.md (draft under ~83H49E3, decisions
D124-D133, not yet landed), read against grmb-spec.md, grimble-model.md
and binding.md in the primary checkout, the owner's mockup and the
coordinator brief.

Citation form: `[A:F22]` is finding F22 of note A; `[F:I-03]` is
implication I-03 of note F; the primary source follows in plain words
(the full reference with DOI or URL is in that note's bibliography).
Strength: S = strong (two or more independent peer-reviewed or
named-company sources, or an official language spec that is itself the
mechanism), M = medium (one strong source or several moderate), W = weak
(one practitioner/opinion source, vendor-curated, or synthesis).

---------------------------------------------------------------------

## 1. Converged findings

Where at least two notes agree independently. Every row carries its
primary sources.

| # | Converged finding | Notes | Primary sources | Str | Consequence for grmb |
|---|---|---|---|---|---|
| K1 | Models are written early, used selectively and informally, then rot unless tied to code. 35 of 50 engineers used no UML, 0 wholeheartedly; GitHub models are created/updated in a short phase at project start | A:F22-F25, C:F1-F2, D:F12, E:F1-F4 | Petre ICSE 2013 (counts via Wilson review), Hebig et al. MODELS 2016 (1.24M projects), Whittle et al. IEEE Software 2014 (450 practitioners), Baltes and Diehl FSE 2014 (394), Akdur et al. JSA 2018 (627 embedded) | S | Binding to code is the survival mechanism, not an extra; every level must be independently useful (no level mandatory) |
| K2 | Practitioners lack analysis, not drawing: satisfied with design capability, dissatisfied with analysis and extra-functional properties | A:F26, C:F4, A:I17 | Malavolta et al. TSE 2013 (48 practitioners, 40 companies) | M | Ship checks (exhaustiveness, binding, close guard, budgets) before renderings |
| K3 | Text is the only source of truth; diagrams are derived and never read back | C:I1-I2, E:I4, F:A-07 | Mermaid in GitHub (2022), LikeC4 layout-drift check, UML 2.5.1 abstract syntax separate from Diagram Interchange | S | Keep `grimble graph --mermaid` pure and golden-tested; no stored layout |
| K4 | Which diagram kinds survive: a structural view and the sequence/interaction view everywhere; state machines only in reactive/embedded work; use-case diagrams common but least informative; communication diagrams dead; a model uses 2-3 kinds | C:7.2, E:F5 and 7.2 | Dobing and Parsons CACM 2006 (full text), Langer et al. Modellierung 2014 (full text), Petre 2013, Akdur 2018 | S | Render sequence per scenario, one structure view, goal tree; drop the use-case diagram |
| K5 | Exhaustive handling of failure outcomes is where production systems die; a catch-all is the hazard | B:F16-F17, E:F26-F27, F:F-01-F-03, C:PLN-003/004 | Yuan et al. OSDI 2014 (92% of catastrophic failures from mishandled non-fatal errors; 35% trivial: empty/log-only handler, over-general catch, TODO in handler), Alquraan et al. OSDI 2018, Maranget JFP 2007, rustc usefulness check, Clippy `wildcard_enum_match_arm` | S | The draft's MDL022-MDL028 core is right; add swallowed-outcome and boundary-failure lints |
| K6 | Two catch-all semantics are needed: one that hides future variants, one that requires all KNOWN variants and warns when a new one lands; plus an owner-side "this set may grow" marker | E:I7, F:I-01-I-03 | Swift SE-0192 `@unknown default` (warning, softened after "a little too aggressive" rollout), Rust RFC 2008 `non_exhaustive` (ignored inside the defining crate), Zig `_` prong (errors if known tags unhandled) | S | `unknown` arm plus `open`/`closed` outcome sets (owner decision D2 for spelling) |
| K7 | Incomplete models need first-class, three-valued treatment; Maybe-only (Must/May/Unknown) is the cheap useful point; full MAVO is an order of magnitude costlier | D:F3-F7, E:F19 and I17, F:F-20 | Famelis thesis 2016, Antonik et al. EATCS 2008 (MTS survey, full text), Siek et al. SNAPL 2015 (gradual guarantee), Libkin TODS 2016 | S | Keep lo/hi; state the gradual guarantee as a tested law; no Var/Abs/OW annotations |
| K8 | A typed hole (`todo`) is the mainstream way to be incomplete on purpose; it must be named, positioned, never silent, gateable at release | D:F9-F10 and I2, F:I-06 and A-04, B:FM-24 | Hazel POPL 2019, GHC typed holes, Agda holes, Clippy `clippy::todo` ("should not be present in production code"), Yuan 2014 (TODO in handlers), Famelis (provisional decisions silently become permanent) | S | Add `todo` as arm body, step, realization or goal leaf, with `until`/`ticket`, Advisory then Warn then release-Error |
| K9 | Strictness must grow with maturity; one strictness level is abandoned or ignored | A:I6 and 7.6, D:I8, E:I17, F:I-07, B:I21 | Uber RFC collapse and tiers (Orosz), Shopify Wedge deferred enforcement, Structure101 "Enforce" flag, Swift softened rollout, Hutchinson et al. ICSE 2011 (progressive adoption) | M | Some authored maturity marker (owner decision D5) |
| K10 | Baseline/ratchet with stale-entry detection is how every conformance tool survives a grown code base; baselines that only grow fail | B:F13, F28-F32, A:I21, E:I12 | ArchUnit FreezingArchRule, jQAssistant baseline, Lattix, Structure101 headless new-only, Shopify Packwerk retrospective (stale entries, violations outpaced fixes), Google AIP linter not semver | S | Adding a planning rule ships Advisory first and graduates through the ratchet; stale accept is a finding (EXC, exists) |
| K11 | Links must be computed and single-sourced; never inferred from commit text or ticket type | A:I20, B:F20 and I10, E:I14-I15, C:I22 | Bachmann et al. FSE 2010, Herzig et al. ICSE 2013 (33.8% misclassified), Rath et al. ICSE 2018 (60% of commits linked; recovery 33% precision), Fucci et al. JSS 2022 (telecom) | S | Confirms D131 (`implements` is the one link); name-similarity binding only as a suggestion |
| K12 | Traceability completeness predicts quality and pays at task level | B:F19 and F26, E:I14, A:F39 | Rempel and Maeder TSE 2017 (24 projects), Maeder and Egyed EMSE 2015 (71 subjects: 24% faster, 50% more correct) | S | Per-level completeness ratio in `grimble status` and a ratchet |
| K13 | Reflexion models are the ancestor of the binding relation; "absence" (declared, not in code) is the half grimble lacks | B:F2-F3 and FM-02, D:F17 and I12, E:[72] | Murphy, Notkin, Sullivan FSE 1995 / TSE 2001 (Microsoft Excel), Li et al. JSEP 2022 (73-study mapping), Lattix "Must Use" | S | Add flow-absent (SYS016); reflexion workflow for first binding |
| K14 | A step that crosses a node boundary or comes from the environment can fail; modeling it infallible is a design omission detectable at design time | B:F16-F17 and FM-22, C:I7 and PLN-005 | Alquraan et al. OSDI 2018 ("the majority could have been avoided by design reviews"), Yuan 2014, Newcombe et al. CACM 2015 (specify environment failure events), P language ghost machines (Desai et al. PLDI 2013) | S | First-build rule PLAN011 (unmodeled boundary failure) |
| K15 | Designers generate alternatives but the reasoning leaves no trace; decisions are recorded after the fact or born "accepted" | A:F45-F46, S66, D:F13-F14 and I6 | Mangano et al. TSE 2015, Cherubini et al. CHI 2007, Parnas and Clements TSE 1986 (policy: record rejected alternatives and why), ICSA 2026 ADR study (63% created already accepted), Buchgeher et al. IEEE Access 2023 (half of ADR repos hold 1-5 records) | M | A cheap alternatives record; whether it is a new entity is owner decision D7 |
| K16 | Design entities go stale while bound code churns; owners and freshness dates counter it | A:P14, F41, C:I17, D:PLN-INC09, E:E-23 | Hebig 2016, Aghajani et al. ICSE 2019, Google SWE book ch. 10 (owners, freshness dates; "Last reviewed by" raised adoption) | M | PLAN022 stale design (Advisory) |
| K17 | Keep the core small and closed; vocabularies are packs; reject GORE machinery, OCL-style expressions and a user-facing transformation language | C:I8, I11, I19, E:I2, I5, A:I27 | Horkoff et al. RE journal 2017, Mavin et al. RE 2017 (goal uptake "quite low"), zur Muehlen and Recker CAiSE 2008 (<20% of BPMN regularly used), Langer 2014, Willink JOT 2020 (OCL 2 "fatally flawed"), Gotz et al. SoSyM 2020 (transformation-language claims unsubstantiated) | S | No AND/OR formulas, softgoals, contribution weights or expression language |
| K18 | Diagnostics decide adoption: one finding per root cause with a site list, attached fixes with applicability, a long-form explain, cascade suppression, measured false-positive budget | F:F-07-F-10, F-26, I-10-I-12, I-16, D:I15, E:I5, C:I6 | Barik et al. ICSE 2017 (13-25% of task time reading errors), Johnson et al. ICSE 2013, Sadowski et al. Tricorder ICSE 2015 (Google), rustc-dev-guide Applicability, Elm "Compilers as Assistants", TypeSpec `defineCodeFix` | S | Diagnostic contract for every planning rule |
| K19 | No authoring order: design is opportunistic, code-first is legitimate, composition is order-independent | D:F14 and I7, C:I14, F:F-22 | Guindon (opportunistic design), Parnas and Clements ("we will never see a software project that proceeds in the rational way"), Curtis et al. CACM 1988, CUE lattice unification | S | Level from construct kind (already D124); missing parent is an obligation, not a parse error |
| K20 | Incremental re-checking at edit time is feasible | D:I11, E:I3 | Egyed TSE 2011 (1.4 ms average, models up to 162,237 elements), Bergmann et al. VIATRA RETE 2008 | M | LSP-first; re-check budget test |
| K21 | Declare a step once and reference it; duplicated example text is the dominant BDD maintenance cost | C:I9-I10, A:I28 | Binamungu et al. SANER 2018 (75 practitioners: frozen specs), Irshad et al. JSS 2021 (Ericsson) | M | Confirms draft 4.4; bind Gherkin by selector via `verified_by`, never adopt Given/When/Then syntax |
| K22 | Per-arm verification obligations, not test generation | A:I11, E:I16, C:PLN-022 | Use-Case 2.0 (test cases are the slice's definition), Utting et al. STVR (coverage-based selection), Alegroth et al. EMSE 2022 (MBT adoption sparse for non-technical reasons); Grieskamp et al. STVR 2011 (MBT works at Microsoft with heavy tooling) | M | Keep PLAN006; no generator in v1 |
| K23 | Extra-functional budgets with units are wanted and checkable | A:I17 and P11, C:I12, B:I19 and FM-36b | Malavolta 2013, AADL (SAE AS5506), Ford et al. fitness functions and Thoughtworks practice (agreed before implementation, run as gates) | M | Step/goal budgets reusing grmb's unit table; quality attribute needs `verified_by` |
| K24 | Retry belongs at one layer and only on idempotent operations | B:F34, FM-23, FM-35 | AWS Builders' Library "Timeouts, retries and backoff with jitter" (five layers of three retries = 243x load; side-effecting APIs unsafe to retry without idempotency) | M (G2 first-party) | Retry lints beyond `max` |
| K25 | "GRL" names two things: ITU-T Z.151 Goal-oriented Requirement Language and grimble's rule language; grmb now adds goals | C:F6 and 7.3, E:7.3 | ITU-T Z.151 (10/2018, in force); jUCMNav legacy repo, last push 2021 | S (fact) | Owner decision D6 |

---------------------------------------------------------------------

## 2. Conflicts between notes, and how the evidence resolves them

| # | Conflict | Positions | Resolution | Decided by |
|---|---|---|---|---|
| X1 | Outcome sets declared or inferred | F:I-04 and A-03.2 infer a step's outcome from its arms (Roc, Zig inferred sets); draft 4.4 and C:I9 declare once; E:I1 makes variant sets first-class graph nodes | Declared wins. The outcome IS the Sig facet whose change propagates (draft 4.4, 8.2); inferring it from arms means adding an arm silently changes the type, which removes the compile-error propagation the layer exists for. Zig's own doc says to switch to explicit sets at boundaries [F:F-05]. Keep inference as an authoring aid only: an undeclared step used in a sketch defaults to `{ ok }`, and an LSP action "declare step from arms" writes the line | coordinator (C1, C6 below) |
| X2 | Keyword vs symbol operators | F originally "evidence leans keyword"; its verification pass withdrew that: Stefik and Siebert TOCE 2013 tested novice writers, not arrows, and found `then`/`end` as error-prone as `==` | Evidence neutral; nothing argues against the mockup's symbols. One spelling, no alias dialect, test the tokens with users | owner D1 |
| X3 | Wildcard forms | Draft: `_` Warn (MDL028). E:I7: `else` (hides, Warn) plus `unknown`. F:I-01/I-02: keep `_` Warn plus `unknown`. C:PLN-004 fires only with two or more non-ok variants | Two forms are supported by SE-0192/RFC 2008/Zig. `else` is already a body word in `retry ... else`, which argues for keeping `_` as the hiding form. C's ">= 2 variants" threshold has no source; drop it | owner D2 (spelling); semantics coordinator |
| X4 | Form of staged strictness | A:I6 three stages sketch/draft/committed with stage-inversion rule; E:I17 `draft` until `ready`; F:I-07 `status draft|ready`, default draft, and says "no direct precedent"; D:I8 `stage draft` scope; B:I21 enforce per node once isolated (Shopify, Structure101) | The need converges (K9); the form does not. Tool precedent exists at scope level (Structure101 diagram Enforce flag, Shopify per-component enforcement), not per language construct. A:I1 also warns against authored workflow status. Taste and trade-off | owner D5 |
| X5 | Goal block meaning | Draft 4.3 calls nesting "OR refinement (KAOS)" and the Rust reading an enum, yet PLAN001 requires EVERY leaf to be realized (an AND reading). E:I8 flags the contradiction; C:I8 rejects KAOS/GRL AND/OR formula machinery | The draft is internally inconsistent and must change either way. Minimal fix uses no formulas: group kinds `all` (default) and `one_of` | owner D3 |
| X6 | Cycle and chatty-pair rules over flows | B:FM-01 (cycle in declared flows) and FM-08 (flows in both directions) assume flows are dependencies | grmb flows are DATA MOVEMENT (D107; grmb-spec 11: "Cyclic flows are allowed"); the draft's own web example declares `f_ui_api` and `f_api_ui`, so FM-01/FM-08 would fire on every request/response pair. Apply FM-01 and FM-05 only to owner-projected CODE dependency edges; drop the flow half of FM-08 | coordinator |
| X7 | Per-symbol privacy | B:FM-11 surface-bypass Warn; B's own verification flipped it to opt-in Advisory | Packwerk retrospective (privacy checks removed in 3.0, unfixable piles) beats the tool-doc evidence; coarse gateway-bypass (FM-38, Uber DOMA) goes to core instead | coordinator (B:7.6) |
| X8 | Organisational metrics | B:I12 REJECT, then ADAPT as opt-in pack | Nagappan et al. ICSE 2008 (Windows Vista: org metrics beat code metrics) is one company; opt-in Advisory pack | coordinator |
| X9 | Review gating | A:F4 Ubl "a dangerous trap of overhead"; A:F41 Google SWE book "most teams require an approved design document"; A:F42 HashiCorp approve-then-implement | Both true at different tiers (A:7.6). Tiered, opt-in | owner D8 |
| X10 | Renderings | Draft 11: sequence, activity and use-case diagrams | K4 is decisive: keep sequence, add structure view and goal tree, drop use-case diagram, activity optional | coordinator |
| X11 | Test generation | E:I16 obligations not generation; E:7.3 notes Grieskamp et al. STVR 2011 (MBT "works and scales" at Microsoft) | Not flipped: the cost there is model upkeep and tooling; keep obligations in v1, a generator stays a later option | coordinator |
| X12 | Decisions in the language | A:I2 new `decision` (ADR) entity; D:I6 `choice` with May members and `rejected because=`; grmb-spec 4.5 already has `vmodel kind decision` with `decides` and `supersedes ... because=` | Evidence supports recording alternatives (K15) but ADR adoption is low (Buchgeher; ICSA 2026) and an entity already exists | owner D7 |
| X13 | Boundary-failure trigger | B:FM-22 triggers on node crossing; C:PLN-005 on actor kind | Not a conflict: union both triggers in one rule (PLAN011); the actor-kind half is model-only and can ship before node location (P6) | coordinator |

---------------------------------------------------------------------

## 3. Change list against grmb-planning.md

Strength: ADOPT (take as is) or ADAPT (take changed). Decider: COORD
(evidence decisive, the coordinator records it) or OWNER (taste or a
trade-off the evidence does not settle; see section 5). Milestone is the
draft's P1-P6 cut (section 15 of the draft).

| # | Section | Change | Rationale (citations) | Tag | Decider | Ms |
|---|---|---|---|---|---|---|
| C1 | 1, 15 | State that every level is independently optional: a model of only goals, only scenarios, or only impls checks free of Errors; the absent level is an Advisory obligation at most. Add one conformance fixture per level subset | K1, K19; E:I18; C:I4 as qualified by Bosch DEPLOY ("only where and when it is really suitable", Mazzara et al. 2012); Whittle 2014 (key parts only) | ADOPT | COORD | P1 |
| C2 | 2.2, 3, 5.3 | Operator spelling: keep the mockup symbols (`->`, `=>`, `-|>`, `-?>`), one spelling, no alias dialect; add a P0 think-aloud check of the tokens before the grammar freezes | X2; F:F-15 and 7 (Stefik and Siebert TOCE 2013, neutral); gofmt and PEP 20 (one way) | ADOPT | OWNER D1 | P0/P1 |
| C3 | 3, 5.3, 7.1 | Two catch-all arms: `_` (matches anything, hides future variants, MDL028 Warn as now) and `unknown` (legal only when every known variant has its own arm, MDL032 Error otherwise; when a variant is added later and only `unknown` covers it, PLAN017 Warn naming variant and sites). Quick-fix `_` to `unknown` | K5, K6; E:I7, E-05, E-06; F:I-01, I-02, ERG005; SE-0192, Zig `_` prong, Clippy wildcard lints | ADAPT | OWNER D2 | P1 (MDL032), P2 (PLAN017 needs lock) |
| C4 | 4.4, 5.3, 7.1 | Outcome sets carry `closed` (default) or `open`. `open` relaxes only matches written outside the owning actor or pack: such a match needs `unknown` or `_` (MDL033 Error otherwise); the owner's own scenarios stay exhaustive. Intended for external actors (payment gateway decline codes) | K6; E:I7, E-07; F:I-03, ERG007; Rust RFC 2008 ("essentially ignored" inside the defining crate) | ADOPT | OWNER D2 | P1 |
| C5 | 4.3, 5.2, 7.2 | Fix the OR/AND contradiction in goal blocks: group kind `all` (default: every leaf needs a realizing scenario, PLAN001) and `one_of` (at least one leaf realized, PLAN018; `exclusive` makes two realized leaves MDL034 Error). Checker reports the kind it assumed. Remove the "KAOS OR refinement" wording | X5; E:I8, E-11-E-13; feature-model groups (Berger et al. TSE 2013, Kconfig `choice`), Alloy `extends` vs `in`; C:I8 (no AND/OR formulas: Horkoff 2017, Mavin 2017) | ADAPT | OWNER D3 | P1/P2 |
| C6 | 4.4, 3 notes | Outcome stays declared and is the source of truth (Sig facet). An undeclared step used in a chain is implicitly `{ ok }` ONLY inside a draft scope (C9); elsewhere MDL006 as now. LSP action "declare step from arms"; an arm naming a variant the implicit `{ ok }` lacks is MDL025 with that fix attached | X1; F:F-05 (Zig: explicit sets at boundaries), F:I-04 (rejected as source of truth, kept as aid), C:I9 | ADAPT | COORD | P1 |
| C7 | 5.3, 7.1 (MDL025), 8 | Exhaustiveness is a flat set difference; MDL022/MDL025 diagnostics print an outcome-set diff (missing and extra variants only), name sites as secondary spans, and split MDL025's messages into redundant arm, foreign variant and equal-specificity tie | K18; E:I6, E-02, E-03 (Maranget JFP 2007; rustc usefulness); F:F-26 (Elm "type diffs") | ADOPT | COORD | P1 |
| C8 | 2.1, 3, 4, 5, 7.2 (new) | Typed hole `todo [because="..."] [ticket=ID] [until=DATE]` legal as arm body, chain element, realization right-hand side, goal leaf and outcome variant. Contributes Unknown to dependents; dependents report one Unresolved naming the hole; `todo` is a contextual body word. PLAN015: Advisory while present, Warn past `until`, Error under a release profile; a hole needs `ticket` or `until` | K8; D:I2, I5, PLN-INC01-03; F:I-06, A-04.3, ERG009; B:FM-24; Hazel POPL 2019, GHC, Clippy `todo`, Yuan 2014, Famelis 2016 (silent permanence) | ADOPT | COORD | P1 (syntax), P2 (rule) |
| C9 | new 7.0 "Strictness", 7.2 | Authored maturity marker that scales severity (draft scope: obligations silent or Advisory, implicit steps and holes allowed, exhaustiveness Advisory; normal scope: the current tables; release profile: holes and drafts Error). Form per owner decision | K9, X4; A:I6, P07, P20; D:I8; E:I17, E-24; F:I-07, A-06.2; B:I21 (Structure101 Enforce, Shopify Wedge); Swift SE-0192 rollout | ADAPT | OWNER D5 | P1 (marker), P2 (severity function) |
| C10 | 5 (new 5.9 "Laws") | State the gradual guarantee: replacing a binding or entity by a less precise one (Must to May, bound to declared, removing a `verified_by`, inserting `todo`) moves verdicts only toward Unresolved; precision adds Fail only where the new precision is wrong. Precondition: consistency (lo subset of hi). Property test in the corpus | K7; D:I4, PLN-INC07, PLN-INC15; Siek et al. SNAPL 2015; Antonik et al. 2008 (inconsistent modal spec validates every property) | ADOPT | COORD | P1 (test), P2 |
| C11 | 7 preamble, 10.5 | Diagnostic contract: one finding per root cause; a variant addition is ONE finding keyed on (step, variant) with every handling site as secondary spans, and `frob plan --findings` files one task per key; a scenario with an unresolved reference or hole suppresses its downstream reachability/termination findings (one Unresolved) | K18; F:I-10, I-16, A-04.1, A-06.1, ERG010, ERG012; D:I15, PLN-INC08; Hazel; rustc multi-span | ADOPT | COORD | P1 |
| C12 | 7 preamble, 15 | Every planning rule declares a fix kind and rustc-style applicability; `grimble fix` applies only MachineApplicable; fixes are local rewrites whose golden test asserts the fixed example has zero findings of that rule; `grimble explain RULE` long form for every id | K18; F:I-11, I-12 (rustc `--explain`, 2025 Rust survey: explanations useful); C:I6 (TypeSpec); E:I5 (graph-rewrite discipline), E-25 | ADOPT | COORD | P1 |
| C13 | 7.2 | Add PLAN011 unmodeled boundary failure: a step owned by an `external`, `device` or `timer` actor, or a step use whose node differs from its predecessor's, with outcome `{ ok }` only. Warn. FIRST BUILD (actor half in P2 model-only; node half in P6) | K14; B:FM-22 (Alquraan OSDI 2018, Yuan OSDI 2014); C:I7, PLN-005 (Newcombe CACM 2015; P ghost machines) | ADOPT | COORD | P2, P6 |
| C14 | 7.2 | Add PLAN012 swallowed outcome: a non-ok arm whose chain is `end ok` with no intervening step. Warn. FIRST BUILD | K5; B:FM-20 (Yuan 2014: empty or log-only handlers) | ADOPT | COORD | P1/P2 |
| C15 | 5.5, 7.2 | Retry: PLAN016 retry hazard: retry of a step whose impl is not marked `idempotent` (pack attribute), `max` above a profile bound, or more than one retry toward the same downstream node on one path. Warn. Record that 16.2 question 3 (time bound) should reuse the existing `bound latency` metric vocabulary | K24; B:F34, FM-23, FM-35 (AWS Builders' Library) | ADOPT | COORD | P2, P6 |
| C16 | 7.2 | Add PLAN014 dead/empty: a step used by no scenario, an actor that owns no step, an empty goal block or outcome set. Advisory | E:I10, E-09, E-10 (Alloy reference: an abstract sig with no extensions "is likely an indication that the model is incomplete") | ADOPT | COORD | P2 |
| C17 | 11, 14, 15 (P5) | Renderings: (1) sequence diagram per scenario with exactly one `alt` branch per handled non-ok arm (an exhaustiveness witness), (2) one structure view of nodes and declared flows, (3) goal tree as a plain tree; activity diagram optional; NO use-case or communication diagram; state diagram only for the later `machine`. Update the UML mapping table and P5 exit | K4, X10; C:7.3 I23; E:7.2; Dobing and Parsons 2006, Langer 2014, Petre 2013, Akdur 2018; FizzBee generates the same pair | ADOPT | COORD | P5 |
| C18 | 11 | Add `grimble show --prose SCENARIO`: numbered English steps derived from U, the review artefact for PMs and designers | F:A-07.2, F-21 (Newcombe: PlusCal front end let engineers learn TLA+ in 2-3 weeks) | ADOPT | COORD | P5 |
| C19 | 6.5 (cross-doc: binding.md 6) | Add SYS016 flow absent (reflexion absence): a declared flow A to B, both owners non-empty, with no code edge between them in either direction; Unresolved on opaque cones or F0 fidelity. Warn. FIRST BUILD. SYS013 (divergence) and SYS016 report together | K13; B:FM-02, F28 (Lattix "Must Use"); D:F17; Murphy et al. 1995/2001 | ADOPT | COORD | P6 |
| C20 | 5.8, 9 | Per-level completeness ratios (bound, verified, implemented) in `grimble status` and graph JSON `rollup`; PLAN021 completeness regression against the lock (Advisory ratchet) | K12; B:FM-26; E:I14, E-19; Rempel and Maeder 2017; Maeder and Egyed 2015 | ADOPT | COORD | P2 |
| C21 | 10.3 | Add PLAN022 stale design (bound code changed in k commits since the entity's span last changed or was acked; Advisory) and owner/freshness metadata usable by it | K16; A:I32, P14, P26; C:I17; D:PLN-INC09; E:E-23; Google SWE book ch. 10 | ADOPT | COORD | P4 |
| C22 | 10.3, 7.4 | Add PM040 moving target (a goal or scenario Body digest changed after an implementing ticket entered in-progress; Advisory) and PM041 implements-level mismatch (epic/story/task vs goal/scenario/impl; Warn) | A:I19, P15 (NaPiRE: moving targets, Mendez Fernandez et al. EMSE 2016); B:FM-28 (Herzig ICSE 2013) | ADOPT | COORD | P3 |
| C23 | 4.3, 7.2 | `non_goal NAME because="...";` inside a goal block (a goal that could reasonably be one but explicitly is not); a scenario realizing it is PLAN027 Warn | A:I3, P05 (Ubl, Google design docs: non-goals); A:F42 (HashiCorp PRD scope) | ADAPT (W) | COORD | P2 |
| C24 | 4.4, 4.3, 7.2 | Budgets with units on steps and goals, reusing grmb-spec's `bound` metric vocabulary and unit table (no new grammar beyond the clause position); PLAN024 path sum exceeds goal budget (Warn); PLAN025 goal quality attribute without `verified_by` at normal strictness (Warn, the fitness-function check) | K2, K23; A:I17, P11; C:I12, PLN-017 (MDL009 covers unit mismatch); B:I19, FM-36b | ADAPT | COORD | P7 (new, after P6) |
| C25 | 6.1, 10.5 | Name-similarity binding suggestions (`grimble bind --suggest`, LSP) are never machine-applicable; grimble never writes a binding without explicit user action | K11; E:I15 (Antoniol TSE 2002; Rath ICSE 2018: 33% precision); D:I10 (one-way, lens laws) | ADOPT | COORD | P2 |
| C26 | 2.3, 3 | Quick-fix for the mockup's string names: `"place-order"` becomes `place_order title "place order"`; the MDL000 message states the rule once and offers the fix | F:A-02 (identifiers protect refactoring; rustc help style); grmb-spec 2.7 | ADOPT | COORD | P1 |
| C27 | 8.3 | Drop arrow alignment in arm blocks; one arm per line with trailing separators, so two authors adding arms touch disjoint lines; arms still sort by variant (stable append positions); chains never reorder | F:A-05.3, I-13 (reasoning only, W) | ADAPT (W) | COORD | P1 |
| C28 | 4.2, 16.1 item 3 | Actor kind for peer systems: keep `external` or restore the mockup's `system` | X-none; see D4 | ADOPT/ADAPT | OWNER D4 | P1 |
| C29 | 2.1, glossary | Record the GRL acronym clash and pick a policy | K25 | ADAPT | OWNER D6 | doc |
| C30 | 16.2 (new item), 6.3 | Decision record: reuse `vmodel kind decision` (with `decides` already admitting planning targets, 6.3) or add `decision`/`choice` | K15, X12 | ADAPT | OWNER D7 | P3 or later |
| C31 | 10.4 (new tier) | Approval gating for the highest tier only (opt-in): an unacked committed planning entity blocks its implementing ticket from entering in-progress (PM043) | X9; A:7.6, P28 | ADAPT | OWNER D8 | P3 |
| C32 | 15 | Add P0 before P1: think-aloud session (3 PMs, 3 designers, 3 embedded engineers; first scenario with one failure branch unaided under 15 minutes; per-token accuracy) and a Cognitive Dimensions questionnaire for the planning layer; same shape as D80's GRL newcomer test | F:A-07.4, F-18 (Myers et al. CHI 2016, IEEE Computer 2016); D:I16 (Green and Blackwell 1998) | ADOPT | COORD | P0 |
| C33 | 15 | Incremental re-check budget test (single-entity edit re-check under a stated threshold on the corpus); LSP checks MDL rules on the model alone, binding findings asynchronous and labelled stale | K20; D:I11; E:I3; F:A-08d (Rust survey: slow tooling tops complaints) | ADOPT | COORD | P1/P2 |
| C34 | 5.2, 16.2 item 4 | Answer open question 4 with a guideline: a variant chosen by an INPUT (role, intent: guest vs account) is a goal variant; one chosen by a step OUTCOME is an arm. PLAN020 variant-duplicated-as-arm, Advisory, off by default | E:I9, E-15 (synthesis, W) | ADAPT (W) | COORD | P2 |
| C35 | 7.2 | Ship every new PLAN rule Advisory first and graduate it by ratchet (rules.md profiles); no rule enters at Error without a measured false-positive budget on the corpus | K10, K18; A:I21 (AIP linter); F:A-06.4 (Tricorder); B:F32 (Packwerk) | ADOPT | COORD | all |
| C36 | 16.2 | Replace the open-question list with section 6 of this note (R2 questions) | this note | ADOPT | COORD | doc |

Not adopted (recorded so they are not re-proposed): Gherkin syntax in
the design layer [A:I28]; event-storming or domain-storytelling grammar
[A:I27, no effectiveness study found]; whole-system generation [A:I29];
OCL/expressions [C:I19]; SysML v2 as the model [C:I20, export seam only];
a user-facing transformation language [E:I5]; GORE softgoals and
contributions [C:I8]; Belnap fourth value [D:I13]; a visual editor in R1
[F:I-20]; hyphenated identifier aliases [F:I-14]; banning shadowing
[F:I-17]; labeled blocks [F:I-18]; goal fan-out limits (no source,
C:PLN-012).

---------------------------------------------------------------------

## 4. Prioritized rule set (merged, deduplicated)

Families as in grmb-planning.md: MDL (grimble-model, well-formedness,
draft holds MDL022-MDL031), PLAN (grimble-bind, obligations and
coverage, draft holds PLAN001-PLAN010), SYS (grimble-bind, binding.md;
SYS014 is reserved for surface, the draft takes SYS015), PM (frob-pm,
draft takes PM037-PM039). Polarity as binding.md 6: P+ presence, P-
absence, P0 mismatch. "if Dn" marks a rule that exists only if owner
decision Dn goes that way. FB = first-build set (build first; strongest
evidence for checks no existing rule covers, plus the core the draft
already has).

### 4.1 Planning-layer rules

| Final id | Alias | Merges | Pol | Default sev | Str | Source | FB / Ms |
|---|---|---|---|---|---|---|---|
| MDL022 | MDL-NONEXHAUSTIVE | draft; E-01, C:PLN-003, A:PLAN-P10, F:ERG012 (grouping) | P- | Error | S | Yuan 2014; Maranget 2007; rustc | FB P1 |
| MDL023 | MDL-UNHANDLED | draft | P- | Error | S | Zig error sets; Yuan 2014 | FB P1 |
| MDL024 | MDL-FALLIBLE-SEQUENCE | draft | P+ | Error | S | Zig `try` semantics | FB P1 |
| MDL025 | MDL-UNREACHABLE-ARM | draft; E-02 redundant arm, E-03 foreign variant, F:ERG001/ERG006 (absorbed via C6) | P+ | Error | S | Maranget; rustc usefulness | FB P1 |
| MDL026 | MDL-UNTERMINATED | draft; F:ERG011 (recursion impossible: include graph acyclic) | P+ | Error | S | Zig inferred sets and recursion | FB P1 |
| MDL027 | MDL-RETRY | draft; B:FM-23 (missing `max` half) | P+ | Error | M | AWS Builders' Library | FB P1 |
| MDL028 | MDL-WILDCARD-ARM | draft; B:FM-21, C:PLN-004 (threshold dropped), E-04, F:ERG004 | P+ | Warn | S | Clippy wildcard lints; Yuan over-general catch | FB P1 |
| MDL029 | MDL-SCENARIO-START | draft; C:PLN-006 | P- | Error | M | P ghost machines; Newcombe | FB P1 |
| MDL030 | MDL-REQUIRES-CYCLE | draft; C:PLN-011 | P+ | Error | M | goal refinement acyclicity (van Lamsweerde) | FB P1 |
| MDL031 | MDL-PLANNING | draft | P+ | Error | - | structural | FB P1 |
| MDL032 | MDL-UNKNOWN-INCOMPLETE | E-05 | P- | Error | S | Zig `_` prong; SE-0192 | P1 (if D2) |
| MDL033 | MDL-OPEN-PLAIN-MATCH | E-07, F:ERG007 | P- | Error | S | RFC 2008 | P1 (if D2) |
| MDL034 | MDL-EXCLUSIVE-GROUP | E-13 | P+ | Error | M | Alloy `extends` disjointness; feature-model xor | P2 (if D3) |
| PLAN001 | PLAN-UNREALIZED-GOAL | draft; C:PLN-001, A:PLAN-P09 (leaf), E-11 | P- | Advisory | S | Newcombe ladder; OpenFastTrace; Rempel and Maeder | FB P2 |
| PLAN002 | PLAN-COARSE-REALIZATION | draft | P+ | Warn | M | same rationale as MDL028 | P2 |
| PLAN003 | PLAN-UNIMPLEMENTED-STEP | draft; C:PLN-002 | P- | Advisory | S | as PLAN001 | FB P2 |
| PLAN004 | PLAN-UNBOUND-IMPL | draft; C:PLN-008, B:FM-14 (vacuity extends to impl and `verified_by` selectors) | P- | Advisory | S | ArchUnit "fail on empty should" | FB P2 |
| PLAN005 | PLAN-UNVERIFIED | draft; C:PLN-022, B:FM-27 | P- | Advisory | M | V-model closure; Rempel and Maeder | FB P2 |
| PLAN006 | PLAN-ARM-UNCOVERED | draft; A:PLAN-P12, E-20 | P- | Advisory | M | Use-Case 2.0 slices; Utting MBT taxonomy | P4 |
| PLAN007 | PLAN-AFFORDANCE | draft | P0 | Warn | W | pack design | P2 |
| PLAN008 | PLAN-PAGE-UNREACHABLE | draft; B:FM-15 (page half) | P- | Warn | M | dependency-cruiser `reachable`/orphans; Shape Up breadboards | P2 |
| PLAN009 | PLAN-NODE-MISMATCH | draft | P0 | Warn | M | reflexion mapping | P6 |
| PLAN010 | PLAN-UNJUSTIFIED-SCENARIO | draft; A:PLAN-P09 (scenario), A:P27 (scenario half), A:P13 and D:PLN-INC12 (kernel "unjustified design") | P- | Warn | M | DDD MSR 25.3% no business context (Ozkan et al. preprint) | P2 |
| PLAN011 | PLAN-BOUNDARY-INFALLIBLE | B:FM-22, C:PLN-005, C:I7 | P- | Warn | S | Alquraan OSDI 2018; Yuan 2014; Newcombe 2015 | FB P2 (actor half), P6 (node half) |
| PLAN012 | PLAN-SWALLOWED-OUTCOME | B:FM-20 | P+ | Warn | S | Yuan 2014 trivial patterns | FB P1/P2 |
| PLAN013 | PLAN-HAPPY-PATH-ONLY | B:FM-25 | P- | Advisory | W | inference from Yuan/Alquraan; Anda and Sjoberg (students) | P2 |
| PLAN014 | PLAN-DEAD-OR-EMPTY | E-09, E-10 | P- | Advisory | M | Alloy reference | P2 |
| PLAN015 | PLAN-HOLE | D:PLN-INC01-03, F:ERG009, B:FM-24, D:PLN-INC04 (shape is positional) | P+ | Advisory; Warn past `until`; Error under release profile | S | Clippy `todo`; Hazel; Famelis | FB P2 |
| PLAN016 | PLAN-RETRY-HAZARD | B:FM-23 (idempotency, bound), FM-35 | P+ | Warn | M (G2) | AWS Builders' Library | P2, P6 |
| PLAN017 | PLAN-UNKNOWN-ABSORBED | E-06, F:ERG005, D:PLN-INC11 | P0 (vs lock) | Warn | S | SE-0192 | P2 (if D2) |
| PLAN018 | PLAN-ONE-OF-EMPTY | E-12 | P- | Advisory | M | feature-model `or` groups | P2 (if D3) |
| PLAN019 | PLAN-REDUNDANT-REQUIRES | E-14 | P+ | Advisory | W | transitive reduction | P2 |
| PLAN020 | PLAN-VARIANT-AS-ARM | E-15 | P0 | Advisory, off | W | synthesis (E:I9) | P2 |
| PLAN021 | PLAN-COMPLETENESS-REGRESSION | E-19, B:FM-26 | P0 (vs lock) | Advisory ratchet | S | Rempel and Maeder; Maeder and Egyed | FB P2 |
| PLAN022 | PLAN-STALE-DESIGN | A:P14, C:PLN-009, D:PLN-INC09, E-23 | P0 | Advisory | M | Hebig 2016; Aghajani 2019; Google SWE book | P4 |
| PLAN023 | PLAN-DECLARED-FOREVER | D:PLN-INC10, C:PLN-016, A:P20 | P0 (age) | Advisory | W | Hebig; Famelis | P3 |
| PLAN024 | PLAN-BUDGET-OVERRUN | A:P11, C:PLN-017 (unit half is MDL009) | P0 | Warn | M | Malavolta 2013; AADL | P7 |
| PLAN025 | PLAN-QUALITY-UNVERIFIED | B:FM-36b | P- | Warn | M | fitness functions (Ford et al.; Thoughtworks) | P7 |
| PLAN026 | PLAN-STAGE-INVERSION | A:P07 | P0 | Warn | W | Uber tiers | P2 (if D5 three-level) |
| PLAN027 | PLAN-NON-GOAL-REALIZED | A:P05 | P0 | Warn | W | Ubl (Google design docs) | P2 |
| PLAN028 | PLAN-CHATTY-SCENARIO | B:FM-08 (scenario half only, X6), FM-09 | P+ | Advisory, off (pack) | W | Taibi et al. (perception); thresholds unvalidated | later |
| PLAN029 | PLAN-UNTITLED-RENDERED | F:ERG002 | P- | Advisory | W | F:A-02 | P5 |
| PLAN030 | PLAN-VAGUE-TITLE | B:FM-30, A:P22 | P+ | Advisory, opt-in pack | W | Femmer et al. JSS 2017 (precision 59%) | later |
| PLAN031 | PLAN-BOILERPLATE-ARMS | F:ERG003 | P+ | Advisory | W | F:A-01 | P2 |
| PLAN032 | PLAN-OVERSIZE | A:P17, F:ERG008 | P+ | Advisory | W | Ubl (split long docs); F:A-05 | later |
| PLAN033 | PLAN-OVERBROAD-BINDING | E-22 | P+ | Advisory | W | Rath 2018 (precision) | P2 |
| PLAN034 | PLAN-DUPLICATE-STEP | C:PLN-007 | P+ | Advisory | M | Binamungu 2018; Irshad 2021 | P2 |
| PLAN035 | PLAN-CONCERN-UNADDRESSED | A:P06 (pack triggers) | P- | Advisory, pack | W | Uber templates (GDPR, payments); Ubl | later |
| PLAN040-PLAN045 | decision family | A:P01-P04, P24-P25; D:PLN-INC05-06 | various | Advisory/Warn | M | Nygard; AWS/Azure ADR guidance; ICSA 2026; Parnas and Clements | if D7 (b or c) |
| PM037 | PM-UNPLANNED-OBLIGATION | draft | P- | Advisory | M | Rosik et al. SPE 2010 (detection alone did not prompt removal) | P3 |
| PM038 | PM-IMPLEMENTS-DECLARED | draft; B:FM-29 | P0 | Error | M | PEP 1 "Final" gate; Rosik | FB P3 |
| PM039 | PM-DONE-UNTOUCHED | draft; B:FM-29 | P0 | Warn | M | Bachmann 2010; Herzig 2013 | P3 |
| PM040 | PM-MOVING-TARGET | A:P15 | P0 | Advisory | M | NaPiRE (Mendez Fernandez et al. EMSE 2016) | P3 |
| PM041 | PM-IMPLEMENTS-LEVEL | B:FM-28 | P0 | Warn | M | Herzig 2013 | P3 |
| PM042 | PM-SKIPPED-EVIDENCE | A:P21 | P0 | Warn | W | Binamungu 2018 (frozen specs) | P4 |
| PM043 | PM-UNAPPROVED-START | A:P28 | P0 | Warn (tier 1) | M | Google SWE book; HashiCorp | P3 (if D8) |
| PM044 | PM-UNANCHORED-CHANGE | E-26 | P0 | Advisory, opt-in | W | Rath 2018 (60% linked) | later |
| PM045 | PM-DRAFT-AFTER-DONE | E-24 | P0 | Warn | W | Egyed; Nuseibeh | P3 (if D5) |

### 4.2 Architecture rules surfaced by the notes (binding.md, not grmb-planning.md)

| Final id | Alias | Merges | Pol | Default sev | Str | Source | Note |
|---|---|---|---|---|---|---|---|
| SYS013 | SYS-UNDECLARED-FLOW | existing; B:FM-03 | P+ | Error | S | reflexion divergence | report with SYS016 |
| SYS014 | SYS-SURFACE (reserved) | B:FM-11 | P+ | Advisory, opt-in | M | Packwerk retrospective flipped it | coarse form is SYS020 |
| SYS015 | SYS-BEHAVIOR-FLOW | draft; C:PLN-010, C:I13 | P+ | Error | M | AADL/ArchiMate cross-layer consistency | P6 |
| SYS016 | SYS-FLOW-ABSENT | B:FM-02 | P- | Warn | S | Murphy et al.; Lattix Must Use | FB (P6 or binding G11) |
| SYS017 | SYS-DEPENDENCY-CYCLE | B:FM-01 (code edges only, X6) | P+ | Advisory | S | Li et al. ICSA 2022 (cycles among top erosion symptoms); Arcan | flows exempt |
| SYS018 | SYS-HUB | B:FM-04 | P+ | Advisory, pack threshold | M | Arcan HL; dependency-cruiser | |
| SYS019 | SYS-UNSTABLE-DEPENDENCY | B:FM-05 (code edges) | P+ | Advisory | M | Arcan UD; Martin I metric | |
| SYS020 | SYS-GATEWAY-BYPASS | B:FM-38 | P+ | Warn | M | Uber DOMA; Shopify Wedge; Bazel visibility | |
| SYS021 | SYS-BOUNDARY-UNCONTRACTED | B:FM-07 | P- | Warn | M | Taibi API versioning; de Toledo | |
| SYS022 | SYS-LAYER-INVERSION | B:FM-10, B:I18 | P+ | Warn when `layer` declared | M | import-linter Layers; Structure101 Strict | |
| SYS023 | SYS-DEPRECATED-NEW-DEPENDENT | B:FM-37 | P+ | Warn | M | Bazel visibility allowlists | |
| SYS024 | SYS-OVERRIDE-WITHOUT-REASON | B:FM-39 | P- | Warn | M | Lattix, Structure101 allows | |
| (pack) | shared-store, implicit coupling, ownership spread | B:FM-06, FM-12, FM-36 | P+ | Advisory, opt-in | W-M | de Toledo; Mo et al. TSE 2021; Nagappan 2008 | microservices / git-history / org packs |
| (EXC) | stale accept, baseline growth | B:FM-13, FM-34 | P- / P+ | Warn / Advisory | S / M | ArchUnit, jQAssistant, Packwerk | exceptions.md owns |

### 4.3 Absorbed or test-time (no user rule)

| Candidate | Where it goes |
|---|---|
| E-16 edge signature, E-17 containment | MDL006 and MDL031 (one namespace, one owning system, draft 4.1) |
| E-18 unstratifiable relation, E-27 closure semantics | GRL compile errors (grl-spec) |
| C:PLN-013 suppression without reason | MDL013 and EXC rules |
| C:PLN-014 order-dependent merge | MDL001 / MDL008 (scalar twice) |
| C:PLN-015 anonymous entity | impossible: names required |
| C:PLN-018 level skipping | impossible: `impl ... for SCENARIO` |
| F:ERG015 stale binding after rename | MDL006, MDL012, SYS008 |
| D:PLN-INC13 hole hides dependency | Unresolved semantics plus C11 cascade |
| E-08 closed set grew | MDL022 already fires |
| C:PLN-019, D:PLN-INC07, F:ERG013, F:ERG014, E-25, C:PLN-021 | conformance tests (collected-set stability, gradual law, fmt never reorders chains, no dialect, fix idempotence, every rule has a fix kind) |
| D:PLN-INC15 | test invariant lo subset of hi; the `choice` half joins PLAN040-045 if D7 |
| D:PLN-INC14 refinement widens | deferred to R2: no planning parent carries a binding yet |
| C:PLN-020 machine state without handler | deferred with the `machine` entity |
| A:P16 glossary, A:P18 attachment, A:P19 rollout gate, A:P23 restated contract | deferred to R2 (entities not admitted) |
| C:PLN-012 goal fan-out | rejected: no source |

### 4.4 First-build set (in order)

1. MDL022-MDL031 as drafted (P1), with C7 diagnostics, C11 grouping and
   cascade, C12 fixes. MDL032/MDL033 join if D2 goes (b).
2. PLAN011 boundary infallible, actor half (P2): the strongest new
   evidence (Alquraan, Yuan, Newcombe) for a check nothing covers.
3. PLAN012 swallowed outcome (P1/P2): Yuan's most common trivial
   pattern, cheap, model-only.
4. PLAN015 hole (P2) together with the `todo` syntax (C8).
5. PLAN001, PLAN003, PLAN004, PLAN005 and PLAN021 completeness (P2).
6. SYS016 flow absent (with the binding G11 work or P6): the other half
   of reflexion, Lattix-proven.
7. PM038 close guard (P3).

---------------------------------------------------------------------

## 5. OWNER DECISIONS

Eight decisions the evidence does not settle. Each: options, evidence,
recommendation.

**D1. Operator spelling.**
Options: (a) keep the mockup's symbols `->` `=>` `-|>` `-?>` as the one
spelling (the current draft); (b) keyword spelling canonical (`then`,
`match`, `try`, `opt`) with symbols as accepted input; (c) keywords only.
Evidence: the only usability study found (Stefik and Siebert, ACM TOCE
2013, full text read) tested never-programmed students writing code; it
did not test arrow operators and found English keywords such as `then`
and `end` as error-prone as `==`. The verification pass withdrew the
earlier "evidence leans keyword" claim: nothing argues against the
mockup's symbols. One spelling per construct is supported by gofmt and
PEP 20; non-programmers are better served by reading a derived prose
and sequence-diagram view (AWS engineers learnt TLA+ through the PlusCal
front end, Newcombe et al. CACM 2015).
Recommendation: (a), no alias dialect, plus a think-aloud test of the
four tokens with 3 PMs, 3 designers and 3 embedded engineers before the
grammar freezes; revisit only a token that fails.

**D2. Catch-all forms (`else`/`unknown`) and `open`/`closed` outcome sets.**
Options: (a) the draft: one `_` arm, Warn; (b) two arms: `_` hides
everything (Warn, as now) and `unknown` is legal only when every known
variant has its own arm, then Warns when a newly added variant lands on
it; plus `closed` (default) or `open` on an outcome set, where `open`
forces matches OUTSIDE the owner to carry `unknown` or `_` and leaves the
owner's own scenarios exhaustive; (c) (b) without `open`/`closed`.
Spelling sub-choice: the hiding arm as `_` (Rust, mockup-compatible) or
`else` (note E's proposal; but `else` is already used by `retry ... max N
else`).
Evidence: Swift SE-0192 `@unknown default` (a warning so adding a case
stays source-compatible; the first rollout as an error was "a little too
aggressive"); Rust RFC 2008 `non_exhaustive` (ignored inside the defining
crate); Zig's `_` prong (errors if a known tag is unhandled); Clippy
treats wildcard arms as latent bugs; Yuan et al. OSDI 2014 (over-general
handlers among the trivial causes of catastrophic failures).
Recommendation: (b) with `_` kept as the hiding arm and `unknown` added;
`open` intended for external actors' outcomes (payment decline codes).

**D3. Goal groups `all` / `one_of`.**
Options: (a) default group kind `all` (every leaf needs a realizing
scenario) and `one_of { ... }` (at least one leaf realized; `exclusive`
makes two an Error); (b) all-of only: record that a goal block means
"every variant must be realized" and model alternatives as separate goals
or as scenario arms; (c) OR-only (the draft's KAOS wording), which
contradicts PLAN001.
Evidence: the draft is internally inconsistent (calls nesting OR
refinement, then requires every leaf). Feature models (mandatory/or/xor;
Kconfig `choice`, Berger et al. TSE 2013) and Alloy (`extends` disjoint vs
`in` overlapping) show "a set of children" is ambiguous without a group
kind. Against more machinery: goal-oriented RE's AND/OR formulas, softgoals
and contributions have low industrial uptake (Horkoff et al. 2017; Mavin
et al. RE 2017, a Rolls-Royce author).
Recommendation: (a), exactly two kinds and one flag, no formulas; the
checker states the kind it assumed.

**D4. Actor kind for peer systems: `external` (draft) vs `system` (mockup).**
Options: (a) `external`, as drafted (matches the core node kind; `system`
is a planning word); (b) allow `system` in actor-kind position only
(contextual after `:`); (c) another word (`peer`, `service`).
Evidence: no empirical source decides spelling. For `system`: C4 and
Structurizr call an external party a "software system" (closeness of
mapping to practitioner vocabulary). For `external`: inside a system,
`system.X` already names a reaction step of the enclosing system, so an
actor kind `system` would put one word on two roles; Cognitive Dimensions
consistency and role-expressiveness (Green and Blackwell 1998) and "one
obvious way" (PEP 20) favour distinct words.
Recommendation: (a) `external`, with an LSP quick-fix from `: system` and
an error message that names the reason.

**D5. Staged strictness vs a single level.**
Options: (a) single level (the draft: well-formedness Errors, planning
obligations Advisory, repository profiles raise them for release); (b)
two levels: an inheritable `draft` marker (per entity, file or system)
under which obligations are silent or Advisory, implicit steps and holes
are allowed and exhaustiveness is Advisory, plus the profiles of (a);
(c) three stages sketch/draft/committed with a stage-inversion rule
(committed depending on sketch is a finding), optionally `provisional`.
Evidence: the need converges across four notes: Uber's RFC process broke
at scale and moved to tiers; Shopify deferred enforcement per component
until it was isolated; Structure101 lets a diagram stay unenforced while
drafted; Swift softened a too-strict rollout; practitioners span sketch to
formal (Whittle 2014, Akdur 2018). Against (c): no language precedent for
per-construct stages (note F), stage-inversion has only one practitioner
source, and authored status rots unless dated (Famelis: provisional
decisions silently become permanent).
Recommendation: (b), with `draft` requiring `until=` or `ticket=` (it is
then checked like a hole) and default = normal strictness so an
unmarked model is checked fully.

**D6. The GRL acronym clash.**
Options: (a) keep "GRL" for grimble's rule language, record the clash,
and never write bare "GRL" in grmb-facing docs, messages or the planning
layer; (b) rename grimble's rule language now (pre-release, cheapest
moment; touches grl-spec.md, D76, D80, rule-authoring, the `.grl`
extension); (c) rename only the user-facing name, keep the file name.
Evidence: ITU-T Z.151 (URN, 10/2018, in force) defines GRL, the
Goal-oriented Requirement Language; grmb now adds goals, so "GRL goal"
is ambiguous in docs and search. Its adoption is academic and regulatory
case studies only, and its reference tool repo is legacy (last push
2021), so the practical collision is in literature and search, not in
users' tools.
Recommendation: (a). The other GRL's user base is small; a rename costs
more than the confusion it avoids, provided grmb docs spell out "grimble
rule language".

**D7. A `decision` / `choice ... rejected because=` entity now?**
Options: (a) not now: reuse the existing `vmodel kind decision` (grmb-spec
4.5: `decides`, `supersedes X because=`; the draft's 6.3 already lets
`decides` target planning entities) and add no grammar; (b) a new ADR-style
`decision` entity (status, options, `affects SELECTOR`, supersession;
immutability once accepted); (c) `choice { a; b chosen; c rejected
because="..."; }` with unchosen members as May until decided.
Evidence for recording alternatives: Parnas and Clements (TSE 1986: record
every rejected alternative and why); Mangano et al. TSE 2015 (alternatives
leave no trace); Thoughtworks Adopt, AWS and Azure ADR guidance. Against a
new entity now: ADR adoption is low (half of GitHub ADR repositories hold
1-5 records, Buchgeher et al. 2023) and 63% of ADRs are created already
"accepted" (ICSA 2026), so a heavy entity may go unused; an entity already
exists.
Recommendation: (a) for P1-P3, plus one corpus case per domain that
records a decision with vmodel; revisit (c) in R2 if the corpus shows
alternatives being lost.

**D8. Review gating before implementation.**
Options: (a) non-blocking: `grimble ack` records review, nothing blocks;
(b) tiered and opt-in: for entities marked tier 1, an unacked committed
change blocks the implementing ticket from entering in-progress (PM043);
(c) blocking everywhere.
Evidence: Ubl (Google) calls reviews "a dangerous trap of overhead"; the
Google SWE book says most Google teams require an approved design doc
before major work; HashiCorp approves RFCs before implementation; Uber
moved to criticality tiers with formal review only for the most critical.
Recommendation: (b), default off, so the common path stays (a).

---------------------------------------------------------------------

## 6. What the mockup corpus must cover next, and R2 questions

### 6.1 Corpus domains (each a `plan/` fixture set with expected findings)

| Domain | Why it will stress the language | Rules and decisions it exercises |
|---|---|---|
| Web shop (exists) | baseline | all P1-P3 |
| Firmware (exists) | timer/device actors, ISR realizations | PLAN007, SYS015, PLAN011 |
| Distributed saga: order, payment, inventory across three nodes with partitions | cross-node failure, retries, compensation, idempotency | PLAN011, PLAN016, SYS015, SYS016, D2 `open` |
| Event-driven / pub-sub service (consumer, cron, fan-out) | no request/response; triggers that are not people; asynchronous succession | MDL029, `Succ` ordering, R2-Q1 |
| CLI developer tool (frob itself, dogfood) | human actor without pages; `cli` affordance | PLAN007, PLAN008 vacuity, C1 level subsets |
| Mobile app with offline sync | state across sessions, conflict resolution | R2-Q2 (`machine`), holes |
| Unity game loop (owner's Unity work) | frame/timer actor, many concurrent systems | R2-Q1, R2-Q3 |
| Batch data pipeline | partial failure, reprocessing, at-least-once | PLAN016, PLAN012 |
| Multi-tenant SaaS admin with roles | actor generalization, alternatives by input | D3, C34, R2-Q9 |
| Regulated (medical or automotive) | full V-model, release profile, every arm verified | PLAN005, PLAN006, D5 release |
| LLM/agent workflow | nondeterministic and growing outcome sets from an external model | D2 `open`, PLAN017 |

### 6.2 Stress cases (each a fixture)

1. Add one variant to a step handled by 40 scenarios: one grouped
   finding, one bulk fix, one `frob plan --findings` task (C11, C12).
2. External open outcome set gains a code: owner exhaustive, consumers
   Warn only (D2).
3. Include chain four deep with `fails with` propagation and one
   `unknown` arm in the middle.
4. Scenario of 20 steps and 12 arms (PLAN032, fmt line behaviour).
5. Fork/join or fire-and-forget step (expected: not expressible; record
   the gap for R2-Q1).
6. Polling or pagination loop that is not a retry.
7. Retry with a time budget rather than a count.
8. Guest vs account modeled both ways (goal `one_of` vs arms) (D3, C34).
9. Code-first: impls bound to existing code before any goal exists (C1,
   PLAN010 as Warn not Error).
10. Model with only goals; model with only impls (C1).
11. Two branches adding different arms to one scenario: textual merge
    must be clean (C27).
12. Step rename with `renamed_from`; `for *` impl across 10 scenarios.
13. Unresolved actor inside a scenario: exactly one finding (C11).
14. Whole model in draft with holes everywhere, then promoted (D5, C8).
15. Inconsistent partial model (a hole on both sides of a flow) must not
    yield a vacuous Pass (C10).
16. PM-authored scenario in the think-aloud session, rendered back as
    prose and sequence diagram (C18, C32).

### 6.3 Open questions for research cycle R2

| # | Question | Why open | Where to look |
|---|---|---|---|
| R2-Q1 | Concurrency and async: does the chain need fork/join, fire-and-forget and event subscription? | No note covered it; corpus cases 5 and the pub-sub domain will hit it | BPMN parallel gateway (in the used core per zur Muehlen), P and Lingua Franca semantics, XState parallel states |
| R2-Q2 | The `machine` entity: exhaustiveness over (state, event), no hierarchy in v1 | Draft open question 1; statecharts survive because executable (C:F15) | SCXML, XState, P state handlers, Akdur (state machines top in embedded) |
| R2-Q3 | Time budgets on steps and retries | Draft open question 3; Builders' Library derives timeouts from latency percentiles | AADL latency analysis, AWS Builders' Library, `bound latency` reuse |
| R2-Q4 | Think-aloud protocol and results for operator tokens and keywords | D1 depends on it | Stefik and Siebert method; Pane et al. IJHCS 2001 (unread); Myers et al. |
| R2-Q5 | Merge behaviour of .grmb in practice | F:A-05 rests on reasoning plus metadata only | Apel et al. FSE 2011 semistructured merge, Accioly et al. EMSE 2017 (both unread) |
| R2-Q6 | Decision records if D7 is (a): do alternatives get lost in the corpus? | D7 revisit trigger | Software Design Decoded insight bodies (unread), Spotify ADR backfill, ICSA 2026 full text |
| R2-Q7 | Trace-based verification (`verified_by trace`) | P4+ option (C:I18) | P PObserve, quint-connect, Cirstea et al. trace validation, MongoDB negative result |
| R2-Q8 | Map the 13 QUS criteria to grammar or lints | A:I18 left unread | Lucassen et al. RE journal 2016 full text |
| R2-Q9 | Actor generalization and roles (admin is also a customer) | not covered; SaaS domain will hit it | UML actor generalization usage, Dobing and Parsons use-case narratives |
| R2-Q10 | Cross-cutting concern packs (security, privacy triggers) | A:I5 design only | Uber template checkpoints, Google design-doc cross-cutting sections, LINDDUN/STRIDE pack shape |
| R2-Q11 | Import/export seams: SysML v2 textual, Structurizr, Backstage descriptors | C:I20/I21 export only | SysML v2 `bnf`, Backstage `source-location` |
| R2-Q12 | Concrete incremental budgets measured on the corpus | C33 threshold is a placeholder | Egyed TSE 2011 setup, rust-analyzer salsa practice |
| R2-Q13 | Goal-tree analyses if D3 is (a): dead leaf, void group | feature-model analyses are background only (E:F25) | Benavides et al. 2010, Batory SPLC 2005 (records only so far) |
| R2-Q14 | Primary texts still unread that a recommendation leans on | honesty | Petre ICSE 2013 full text, Green and Petre JVLC 1996, Cockburn "Writing Effective Use Cases", Bryar and Carr "Working Backwards" |

### 6.4 Draft open questions, status after R1

| Draft 16.2 | Status |
|---|---|
| 1 state machines | open, R2-Q2 |
| 2 generic outcomes over payload | answered: no (E:I11, P has no tagged unions; payloads stay contracts) |
| 3 retry time bound | open, R2-Q3; direction: reuse `bound latency` |
| 4 scenario per refinement vs arms | answered by guideline C34, pending D3 |
| 5 actor as vmodel stakeholder | open, low priority (no evidence either way) |
| 6 PLAN006 satisfied by scenario-level test | answered: no; arm evidence must be explicit (E:I16; Use-Case 2.0 slices) |
