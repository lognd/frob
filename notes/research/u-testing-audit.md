# Audit: rule-testing model (D103) and lint/mdtest/snapshot design versus the universal model U

Read-only audit, 2026-10-06. Output file only. Citation forms: `UM` = docs/design/universal-model.md,
`CM` = code-model.md, `BTC` = build-test-ci.md, `RU` = rules.md, `GRL` = grl-spec.md,
`LR` = notes/research/lint-requirements.md, `DG` = diagnostics.md, `RT` = notes/research/rule-testing.md, `FM` = crates/gob-mdtest/FORMAT.md.
Paths under crates/ are given without the crates/ prefix when unambiguous.

Coverage statement: every file in the brief was read except that codegen-macros.md and rule-testing.md
were read selectively (headings, sections a-d of RT, and every line mentioning unresolved/unknown/opaque/
polarity/fidelity/language, which is zero hits for those words except "language" in the sense of
programming language and parse-error strictness) and paradigms.md/calculi.md only for their conformance and
fidelity-corpus passages (paradigms.md:1198, calculi.md:2087 and 2195). The 15 tickets in the brief were
briefed (all 15 explored, 0 pending, 0 blocked). I also briefed ~VB2EYG6, ~BP7TEN3, ~973VQTH, ~8HJZ9MP,
~X80Q4DH, ~01ENJEW and ~2HHBFSY because they overlap (see 5).

## 0. Verdict in six lines

1. D103 imports ty/ruff's two-valued model (a case either has diagnostics or it does not). U is a
   five-valued world (Fire, Unresolved, Clean, NotApplicable, and "examined N of M"). gob-mdtest can assert
   only Fire (error/warn at a line) and "zero findings"; it cannot assert Unresolved, its reason code,
   Advisory, NotApplicable, subjects examined, fidelity, parse status, or a May-versus-Must outcome.
2. Worse, "expect=clean" is today indistinguishable from "the rule examined nothing". That is the exact
   silent pass UM 4.2 (subject accounting) forbids, reintroduced one layer up, in the tests.
3. The design already contains the right model in two other places (GRL section 9 example kinds `fire`,
   `clean`, `unresolved`, `notapplicable`, `known-gap`, `fixed`; RU section 2 "third fixture ... expecting
   Unresolved or a not-applicable listing and never clean"), and the code already has the machinery in
   three other places (gob-ir RuleOutcome, grimble-bind's bespoke `expect` corpus with `subjects RULE N`
   and `unresolved:reason`, frob-check/tests/fidelity.rs). D103 and its 8 open tickets ignore all of it,
   so there will be four incompatible example formats.
4. The coverage meta-test checks "one fire and one clean block exist anywhere under crates/"; it is blind to
   polarity, tier, must_measure and language, all of which RuleMeta already carries.
5. Cross-language: every production mdtest corpus is Rust or markdown or `text` (66 rust, 14 markdown, 59
   text, 4 py in the toy self-test only, 0 ts, 0 opaque); no universal rule has a test in a second language
   or an F0 file inside mdtest. The promised "third fixture" does not exist (gob-macros has no generation).
6. ruff/ty practices conflict with U in four concrete places (section 3): strict unexpected-finding mode,
   "fix leaves no fixable finding", marker addressing by line, and the message-convention test.

## 1. What U promises that a test must be able to observe

| # | U promise | Where | What a test must be able to say |
|---|---|---|---|
| 1a | Answer lattice Exact / Bounds{lo,hi} / Unknown / NotApplicable; Kleene logic | UM 4.1; gob-ir/src/answer.rs:15 | per rule case: which bound decided the outcome (Must edge vs May edge) |
| 1b | Resolution edges carry Must / May / Unknown | UM 2.2 item 3; gob-ir/src/scope.rs:23 | "this call is a May edge, so P- COV001 is Unresolved, not Fire" |
| 1c | Polarity table: P+ fires on lo, clean when hi empty; P- fires when hi has no good thing, clean when lo has one; P0 both Exact; Pn max/min; Pc path in lo / none in hi; else Unresolved | UM 4.2 table | three outcomes per rule, chosen by polarity: fire / clean / unresolved, each reachable by a small input |
| 1d | "Clean" means different things per polarity (P+: no offender in hi; P-: a good thing in lo; P0: both Exact and equal; Pn: hi <= N or lo >= N; Pc: no path in hi) | UM 4.2 | clean must be certified, so the test must assert the certification, not the absence of output |
| 1e | Unresolved is a finding severity with a reason code (opaque:<code>, hole, edge:may, unknown, vacuous, annotation-required:*, dynamic:*, expansion:budget, normalization:unverified, order:unrecorded), rolled up per rule and artifact, with a remedy | UM 4.2, 4.6; gob-ir/src/eval/program.rs:85; DG 5 ("Unresolved finding" row of diagnostics.md section 5) | assert severity=Unresolved, the reason code, optionally `required`, and that a remedy is rendered |
| 1f | subjects_examined and subjects_total on every rule outcome; zero examined over a not-wholly-NotApplicable scope is Unresolved("vacuous"), never clean (the silent-zero principle); must_measure makes it required | UM 4.2 "Subject accounting", "The gate"; gob-ir/src/eval/program.rs:118-126 | assert `subjects >= 1` on every clean case; assert `subjects = 0` plus vacuous on the vacuous case |
| 1g | NotApplicable is a query answer, excluded from the subject set, never a finding; listed once per language in the fidelity report | UM 4.1, 4.2; fidelity.md | assert zero findings AND subjects_total = 0 AND the not-applicable listing (with reason) |
| 1h | Unknown (adapter did not provide) is Unresolved, distinct from NotApplicable (language has no such feature) | UM 4.1 glossary, 3.3 last paragraph, 6 ("worst case is F0 with everything Unresolved") | one case of each, in the same rule |
| 1i | Fidelity levels F0-F4 per language, graded by a corpus; "A rule needing a level the adapter lacks is Unresolved for that language" | UM 3.3; CM 3 | assert the measured fidelity of the case file; assert a rule whose min level exceeds it is Unresolved |
| 1j | Opaque regions: every structural query Unknown/NotApplicable, EXCEPT lexical queries (text, literals, prose) which are exact on the payload; a rule with an opaque subject reports no Error/Warn on it and one Unresolved naming the reason | UM 2.2 item 4, 4.2 last bullet, 4.6; Q03, Q11, Q14 | two cases per lexical rule: it DOES fire inside an opaque region (CI007 over a shell `run:` body, DK004, secret literals); and a structural rule over the same region is Unresolved |
| 1k | Capability cells Implemented / NotApplicable(reason) / Gap(ticket) per language; unknown cell is Unresolved, not-applicable cell is never | CM 3; UM 8 last bullet; LR 5 (and the proposed fourth `Approximate`) | cell snapshot per language per capability |
| 1l | Parse status Ok / Partial / Failed / NoText / Unsupported (Q02); partial parses are salvaged AND reported; zero symbols from a tree with ERROR nodes is a conformance failure | UM 5 Q02; CM 3 last paragraph | assert parse status; assert a hole caveat Unresolved |
| 1m | Locations are not byte offsets (grid, graph, pointer, notebook cell, stream) | UM 2.5, 8 | markers must address a Location, not only a line |
| 1n | Exceptions: an Unresolved can be parked only by `defer` or `baseline`, never `accept` (EXC016); an Unresolved site is never STALE | UM 4.2 last paragraph | exception-interaction cases (frob-obligations exc*.md exist but none uses Unresolved) |
| 1o | Totality: no adapter can make the pipeline fail; the worst case is one opaque node and Unresolved rules | UM 3.2 | a "garbage and unsupported input never panics, always yields Unresolved or NotApplicable" case per adapter (fuzz/expect-panic covers the panic half only) |
| 1p | Digest scheme: formatting never changes a digest; a token change always does | UM 7.1 | not a rule-test matter; covered by gob-ir/gob-symbols tests (out of scope here) |

## 2. What the current markers and the planned tickets can and cannot assert

### 2.1 Today (code reality)

Runner contract: `Runner<F: Fn(&Case) -> Vec<Finding>>` (gob-mdtest/src/run.rs:155-160). The runner returns only
`Vec<Finding>`. `gob_rules::Finding` (gob-rules/src/finding.rs:92-107) has rule, severity, span (Option), message,
fingerprint, fix, `required: Option<RequiredReason>`. It does NOT have `subjects_examined`, an Unresolved
reason code, `source_rule` or a `Location`, although UM section 8 ("gob-rules: Finding keeps Unresolved and
gains subjects_examined, source_rule and a location") and RU section 2 say it does. The reason code and the
subject count therefore cannot reach mdtest at all, whatever the markers learn to say.

Marker grammar: only `error:` and `warn:` followed by a rule id, matched on (line, rule, severity)
(gob-mdtest/src/parse.rs:111-134, run.rs:148). `Severity` has four values (Unresolved < Advisory < Warn <
Error, gob-rules/src/meta.rs:7-17); two of the four cannot be written as a marker.

Check logic (run.rs:171-203):

- findings are first FILTERED to the block rule plus marker rules (run.rs:174-178); everything else is dropped.
- `expect=clean`: passes iff the filtered set is empty. So an Unresolved from the same rule FAILS a clean block
  (reasonable), but a rule that examined nothing, was NotApplicable, or was silenced by a wrong file extension
  PASSES it. There is no assertion that anything was examined.
- `expect=fire` without markers: passes iff the filtered set is non-empty, of ANY severity. An Unresolved-only
  result passes as "fires". Evidence: frob-obligations/tests/mdtest/inv002.md:25 "Reports an invalid glob as
  unresolved" is an `expect=fire` block with no marker and no severity; it would pass if the rule emitted an
  Error instead, or any other Unresolved for any reason.
- `expect=fire` with markers: exact (line, rule, severity) multiset equality; an Unresolved finding of the same
  rule in the same block makes the case fail with no way to write the expectation.
- spanless findings map to line 0 (run.rs:128-137), which no 1-based marker can match. Rolled-up Unresolved
  findings are spanless by design (UM 4.2 "rolled up per rule and artifact"; gob-check/src/status.rs:183-199
  `opaque_finding` passes `None`), so they are structurally unassertable.

Snapshots (`snapshot-diagnostics`, FM section "Snapshot diagnostics"; run.rs:261-286) render whatever findings
come back through the text renderer. They can lock the text of an Unresolved finding but cannot lock its
reason code (not a field), the subject count, or the fidelity report line. Clean blocks snapshot "the empty
rendering", which is identical for clean, NotApplicable, vacuous-but-not-required and silently-skipped.

Coverage meta-test (gob-mdtest/src/coverage.rs:106-124, 172-203): a rule is covered when its id appears in an
`expect=fire` block anywhere under any crates/*/tests/mdtest and in an `expect=clean` block anywhere (they may
be in different files, languages and crates), or a fixture plus .snap exists. It never reads
`RuleMeta.polarity`, `tier`, `must_measure`, nor the language of the block. The allowlist is keyed by rule only
(coverage-allowlist.toml), so it cannot express "COV001 has fire+clean but lacks the Unresolved case".

Corpus facts (find over crates/*/tests/mdtest): 27 files, 11 for frob-obligations, 5 frob-pm, 3 frob-release,
4 gob-directives, 4 gob-mdtest self-tests. Zero production block uses a non-Rust/markdown/text language; the
word "unresolved" appears once in a corpus (inv002.md:25, quoted above). COV001 is declared P- with
`must_measure = true` (frob-obligations/src/rules.rs:15-27) and cov.rs implements three Unresolved paths
(partial parse cov.rs:~318, May-reach/poison `unresolved_reach` cov.rs:~345, zero test-capable files via
`cov001_subjects` cov.rs:33-47, lib.rs:250) but cov001.md has no block for any of them: six blocks, two fire
and four clean, all Must-edge Rust.

### 2.2 Capability matrix (answers to the specific questions in the brief)

| Can a corpus assert ... | mdtest today | After the 8 D103 tickets as written | Needed |
|---|---|---|---|
| a Fire at a line | yes (error/warn) | yes, plus column and message (~KCJ0F5T) | keep |
| an Advisory finding | no marker word; passes only as unmarked fire | no change | `advisory:` marker |
| an Unresolved finding | no (only by accident, unmarked fire) | no; and under strict (~1X6M6MS) any Unresolved of a selected rule becomes an UNEXPECTED finding and fails the case | `unresolved[reason]:` marker and `expect=unresolved` |
| its reason code | no (not a Finding field; grimble-bind smuggles it in message text as `[sys-unresolved/<code>]`, grimble-bind/src/types.rs:175; gob-check parses `annotation-required:` prefix, gob-check/src/required.rs:12) | no | typed `reason` on Finding, asserted structurally |
| `required` (gate-failing) Unresolved | no | no | `required` attribute on the marker |
| expected subjects_examined count / "clean over N subjects" | no | no | `subjects=N`, `subjects>=N`; default `>=1` for every clean block |
| a vacuous result (zero examined, not NotApplicable) | no | no | `expect=unresolved reason=vacuous` |
| NotApplicable | no (indistinguishable from clean) | no | `expect=notapplicable reason=...` asserting zero findings, subjects_total=0, and the listing |
| May vs Must edge decided the outcome | only indirectly, by crafting source whose adapter happens to produce a May edge; nothing asserts the edge status | no | block attribute `edges=may` is wrong (too internal); instead assert the observable: Fire vs Unresolved(edge:may) vs Clean for the same shape, plus an optional `explain` assertion of the bound used (GRL 7.2 says `rule why` prints it) |
| fidelity level of the case file | no | no | `fidelity=F0..F4` attribute asserting the measured level of the block's file |
| parse status of the case file | no | no | `parse=ok|partial|failed|nottext` |
| opaque region behaviour | no | no | a block in an F0 language and a block with an embedded opaque island |
| a capability cell | no (only gob-symbols/tests/web_corpus.rs, web only, insta text) | no | per-adapter generated matrix snapshot, all adapters (see 4) |
| a rolled-up (spanless) finding | no (line 0) | no | location variants: `file`, `repo`, `cell`, `pointer`; at minimum a header-level `expect` list |
| a finding in a non-text artifact (cell, graph, pointer) | no | no | marker addressing by Location, not only 1-based line |
| a fix converges and does not degrade U (parse status, opaque count) | no | ~G4WAFJT: fixpoint, reparse, no new parse error | add "no new opaque/hole node, same or better fidelity" |

### 2.3 Where U is tested today, outside mdtest (so the design has four example formats)

1. gob-ir/tests/eval.rs: 30 tests of the polarity table, vacuous, must_measure, NotApplicable, opaque cone,
   annotation-required (e.g. `p_plus_over_an_opaque_cone_is_unresolved_never_error_or_clean`, eval.rs:148;
   `zero_subjects_is_vacuous_unresolved_never_clean`, :229). Excellent, but over a hand-built `Model` and a
   closure RuleProgram. No product rule uses `RuleProgram` (grep: only gob-ir), so the claim "the framework
   applies the table, so the adapter-could-not-see-X-and-read-that-as-none cannot be written" (UM 4.2) is
   proven for the evaluator and unproven for every shipped rule (COV001 hand-rolls it in cov.rs).
2. grimble-bind/tests/corpus.rs + 19 case directories: its own `expect` language with `finding RULE
   SEVERITY[:reason] [~substring]`, `subjects RULE N`, `owner ... must|may|unknown|foreign`, `row`, `norow`.
   This is the only place where Unresolved reasons and subject counts are asserted in a corpus, and it is a
   second, incompatible format (corpus/rules_sys005_vacuous/expect: `subjects SYS005 0`).
3. frob-check/tests/fidelity.rs: bespoke Rust asserting opaque F0 text is Unresolved for TODO001/REF001,
   binary is NotApplicable, partial parse adds one Unresolved, `opaque.not_applicable["DOC"] == 2`,
   `files_examined == 0`. This is precisely the third-fixture doctrine, hand-written once for four rules.
4. gob-symbols/tests/corpus.rs (insta snapshots of term, scope graph, symbols, edges per claimed operator) and
   web_corpus.rs (capability matrix snapshot for six web extensions). This is the fidelity corpus of UM 3.3.
5. GRL section 9 / ~VB2EYG6 (blocked, todo): a fifth format, `//~ warn`, `//~ unresolved`, `expect "line 3:
   warn"`, `known-gap`, `fixed`.

D103 chooses mdtest as "the primary rule test" (README D103, BTC 2) without reconciling 2, 3 or 5. Result:
the only format that is the sanctioned primary cannot express the guarantees U exists to provide.

## 3. Where ruff/ty practices adopted in D103 conflict with U

ruff and ty have no Unknown, Unresolved, NotApplicable or subject count (RT mentions none: zero hits for
"unresolved", "opaque", "polarity", "subjects"). Everything they do assumes "a diagnostic is a positive claim
and its absence is a pass". For a linter over a single typed language that is nearly right; for a three-valued
universal tool it is wrong at four points.

3.1 Strict "no unexpected diagnostics" (~1X6M6MS, ty matcher.rs:243-248). In ty an unexpected diagnostic is
always a bug. In frob an Unresolved of the rule under test next to a Fire is routine and correct: a P+ rule
over a file with one macro-expanded region emits its Fire AND one rolled-up Unresolved. As written, the ticket
("fail on any selected finding no marker matches") plus the Error/Warn-only marker grammar makes that
legitimate outcome unwritable (no marker matches a spanless Unresolved), so authors will either delete the
opaque case or add `rules=` selects that hide it. Required change: strictness counts Unresolved and Advisory
findings, markers must be able to match them, and the rolled-up spanless forms need an addressable form.

3.2 "A clean block is a pass" (the ty/ruff control model; FM positive controls; ~BGB8V55). A frob clean block
must additionally prove the rule examined at least one subject, else it re-creates the Kotlin silent-zero
(CM 3 last paragraph, UM 4.2 vacuous). Today `expect=clean file=src/lib.rz` passes forever. D103's "fire-and-
clean controls ... frob additions that neither ruff nor ty has" (BTC 2) is the right instinct but certifies the
wrong thing. Also positive controls are per rule per FILE (run.rs:211-240): two rules in one file each need
their own pair, fine, but neither control checks polarity-appropriate evidence.

3.3 ruff fix invariants (~G4WAFJT, ruff test.rs:232-433, BTC 6). Three of the four invariants are U-neutral
(fixpoint, no oscillation, edits equal output). Two need U-aware rewording: "reparse, no new parse error"
should read "parse status does not degrade (Ok stays Ok, Partial does not gain holes) and the opaque/hole node
count does not increase"; "no fixable finding left" must not count an Unresolved as "left" (an Unresolved is
never fixable; a fix that turns a Fire into an Unresolved because it introduced a dynamic construct is a
FAILING fix, not a converged one). The harness must report outcome-class transitions Fire->Clean (good),
Fire->Unresolved (bad), Fire->Fire (non-converged).

3.4 Marker addressing and snapshots by line. ty/ruff markers are 1-based line, optional column, because every
ty/ruff input is a text file. UM 2.5 (locations) and UM 8 (Finding gains a Location enum; FindingRecord a
location object) make line a derived view. Spreadsheet, notebook, graph and pointer artifacts (UM 6 families
spreadsheets, notebooks, dataflow, config) have no line. D103 should say markers address a Location, with line
as the text-artifact spelling; otherwise universal rules over F3 non-text languages are untestable by
construction.

3.5 Message convention test (~T7EH2BG, clippy lint_message_convention). U-mandated Unresolved messages
currently start with the rule id (`COV001: file parsed partially ...`, gob-check/src/status.rs:150-163
`unresolved_finding` format "{id}: {reason}: {path}") and UM 4.6 / DG section 5 require a remedy naming the
exact annotation. The convention test must (a) define the Unresolved message shape separately and (b) assert
every Unresolved snapshot contains a remedy line and a reason code. Otherwise it will either flag every
Unresolved or ignore them.

3.6 ty `<!-- snapshot-diagnostics -->` per file and inline `snapshot` blocks (~V6ZFY72). Fine for Fires. For
Unresolved the rendered text must include the reason code in words (DG section 5, last row), so snapshotting
it is good, but the update mode (`FROB_MDTEST_UPDATE=1`) must refuse to rewrite a snapshot whose severity class
changed (Fire -> Unresolved) without an explicit flag, or a regression from "decided" to "Unresolved" is
"fixed" by an update. ruff has no analog because it has no third outcome.

3.7 Docs-as-tests: bare `error:` in a rule doc means "this rule fires" (ty lint_docs, ~KCJ0F5T/~D3ZK8NM). For a
rule with polarity P- and must_measure, "Example" must be one of fire/clean/unresolved; the derive-doc template
`What it does / Why it matters / Example` (~D3ZK8NM acceptance 3) has no place for "When it cannot decide"
(UM 4.2 outcomes, DG 5 teaching row). Add a fourth required section.

3.8 Ecosystem check (D98 row, ~9HS3VP7) is the one place the design already counts Unresolved ("per-rule
added/removed/changed findings, crashes, Unresolved deltas and timing"). Keep; add a per-language
`files_examined / files` ratio delta (fidelity.rs already computes it) because a regression to F0 shows up as
fewer findings, which a finding-diff reads as an improvement.

## 4. Cross-language: does the design require universal rules to be tested across languages and fidelity levels?

No. Evidence:

- UM defines universal rules as running "for every language" with per-language outcomes (UM 1 item 2 and 4.2;
  RU section 1 "Two rule tiers"; GRL 7.3). RU section 2 promises a generated third fixture "in a language that
  lacks the feature, expecting Unresolved or a not-applicable listing and never clean". GRL 9 repeats it:
  "A universal rule also needs one notapplicable or unresolved example in a language that lacks the feature".
  Neither is implemented: gob-macros contains no mdtest generation; coverage.rs does not know tier; D103 and
  BTC 6 do not mention it; `FORMAT.md` has no `notapplicable`/`unresolved`.
- 38+ rules are `tier = Universal` (frob-obligations/src/rules.rs, frob-ledger/src/rules.rs, gob-config, ...);
  none has a second-language case in mdtest. DOC001's non-Rust behaviour (NotApplicable for Python, C#, TS;
  fidelity.md table) is tested nowhere in mdtest, only by the hand-written fidelity.rs for a few rules.
- The fidelity table (docs/reference/fidelity.md, hand-written prose) and the code (`gob_check::need_of`,
  gob-check/src/status.rs:66-76, keyed by rule-id STRINGS) duplicate what RU section 2 says is on the derive
  (`needs(Q::...)`). `RuleMeta` has no `needs` field (gob-rules/src/meta.rs:80-120, fidelity.md last paragraph
  admits "The minimum fidelity lives in gob_check::need_of because RuleMeta is declared in gob-rules"). So the
  registry cannot compute which (rule, language) cells exist, and neither can a coverage test.
- Adapter conformance (CM 3 "each adapter ships fixtures/*.{ext} with expected symbols, digests, U terms,
  imports") exists as insta corpora for Rust, Python, C#, markdown (gob-symbols/tests/corpus.rs:12-26 claims
  arrays; :154-178) and web (web_corpus.rs). Gaps against UM 3.3 and CM 3:
  a) Fidelity is asserted as a constant (`assert_eq!(RustAdapter.fidelity(), Fidelity::F3)`, corpus.rs:157), not
     measured. UM 3.3 defines the levels by capability (F2 = binders+Must lexical edges, F3 = resolved apply
     edges, F4 = attributes/comments/regions/phases) but the claims arrays are hand-written operator lists;
     nothing fails if Python is declared F2 yet produces no Must edge, or if C# at F1 starts emitting refs.
  b) No test proves "A rule needing a level the adapter lacks is Unresolved" except fidelity.rs for two rules.
  c) The capability-matrix snapshot covers only the six web extensions (web_corpus.rs:177-205); Rust, Python,
     C#, markdown, TOML, YAML, CSS cells are not snapshot-tested, though `frob doctor --languages` and the README
     language table are to be generated from them (UM 3.3, UM 9 q3).
  d) No F0 adapter conformance (UM 3.2: "the worst case is one opaque node") and no adversarial/garbage input
     per adapter asserting Unresolved-or-NotApplicable rather than panic.
  e) ~01ENJEW (C#) and ~8HJZ9MP (tier-4 packs) each re-invent a fidelity corpus; the only generic statement is
     "fidelity corpus run once per version; language reported at measured, not claimed, level" (~8HJZ9MP
     acceptance 2). That is exactly the missing measurement, but it is scoped to wasm packs only.
- The research already contains the test matrix: LR section 6 ("Rules that are impossible or wrong where a
  feature is missing": rule family x {no files, no names, no static calls, no comments, no text, no
  convention}, cells ok / U / A / C) and LR section 7 (worked per-paradigm outcomes, e.g. line 620 "COV001
  (P-): ... CLEAN", 666 "COV001 UNRESOLVED once (tests None)", 713 "ONE Unresolved per notebook"). UM 6.1
  states "Brainfuck: every rule except SCOPE and digests is NotApplicable". Each of those is an expected
  outcome cell that nobody turns into a test.

### 4.1 A semantic inconsistency the tests would otherwise pin

UM 4.2 and UM 6: an opaque subject yields ONE Unresolved naming the reason, and "the worst case is F0 with
everything Unresolved"; UM 3.3: "A rule needing a level the adapter lacks is Unresolved for that language";
NotApplicable means "the language has no such feature (no comments, no visibility, no tests, no files)".
The shipped behaviour (gob-check/src/status.rs:96-103 and docs/reference/fidelity.md, first table) maps
"Opaque F0 (no adapter), text" with a capability rule (DOC001, DOC002, INV002, COV001) to NotApplicable, i.e.
silent: a `.rb` or `.go` file with no adapter produces no DOC001/COV001 outcome at all except a count in the
fidelity report. "No adapter yet" is Unknown (the adapter does not provide the answer), not NotApplicable (Ruby
does have public methods). Only binary and genuinely featureless artifacts are NotApplicable. This is pinned by
fidelity.rs:107-124 (`opaque.not_applicable["DOC"] == 2`). Either the design (UM 6, 3.3) or the code is wrong; the
tests must follow whichever is chosen, and the choice needs recording (new ticket N8 below). My reading of U:
the code is wrong for text files with no adapter; the fidelity-report listing is the mitigation, and since
UM 4.2 says NotApplicable rules are "listed once per language", a never-Unresolved result is defensible only
if the language is declared featureless. The ambiguity is itself the finding.

## 5. Concrete changes

### 5.1 Target model (one sentence per element, referenced by the amendments below)

Outcome classes (one vocabulary, shared by gob-mdtest, GRL examples and grimble-bind corpus, taken from GRL 9):
`fire`, `clean`, `unresolved`, `notapplicable`, plus modifiers `known-gap` and `fixed`. A case's runner returns a
`RuleReport { rule, subjects_total, subjects_examined, not_applicable: Option<String>, findings }` (gob-rules
type, below gob-ir; gob-ir's `RuleOutcome` converts into it), and `Finding` gains
`reason: Option<UnresolvedReason>` (typed; closed prefixes plus an open code) and a `Location` (UM 8).

Block grammar additions (all optional except where noted):

```
```rust expect=clean file=src/lib.rs subjects>=1          # default for every clean block
```rust expect=unresolved reason=opaque:annotation-required:signature [required]
```py   expect=notapplicable reason="no visibility convention"
```json expect=unresolved reason=vacuous
```rust expect=fire fidelity=F3 parse=partial
```

Markers: `error:`, `warn:`, `advisory:`, `unresolved[reason]:` (+ optional `required`), with column and message
as in ~KCJ0F5T; a trailing `scope=file|repo` header assertion form for spanless findings.

Clean certification: `expect=clean` requires zero findings of the block rule at ANY severity (Unresolved
included) AND `subjects_examined >= 1` AND not NotApplicable. A block that wants a different subject count says
so. This is the executable form of UM 4.2.

Required cases per rule (derivable from `RuleMeta`, hence checkable by coverage.rs):

| Rule property | Required blocks |
|---|---|
| any | fire, clean(subjects>=1) |
| polarity P+ | unresolved: offender present only on a May edge or inside an opaque region |
| polarity P- | unresolved: good thing present only on a May edge / test_items Unknown |
| polarity P0 | unresolved: one side not Exact |
| polarity Pn | unresolved: lo <= N < hi |
| polarity Pc | unresolved: path only through May edges, poisoned frontier named |
| tier Universal | one `notapplicable` or `unresolved` block in a language lacking the feature, plus the cross-language rows below |
| must_measure | `expect=unresolved reason=vacuous required` |
| lexical rule (needs only Q03/Q11/Q14) | one fire INSIDE an opaque region |

### 5.2 Amendments to existing tickets

| Ticket | Add to scope / acceptance |
|---|---|
| ~1X6M6MS strict mode | Acceptance 3: "an Unresolved or Advisory finding of a selected rule that no marker matches fails the case; markers `advisory:` and `unresolved[reason]:` exist and match; a rolled-up spanless Unresolved is matched by a header assertion". Acceptance 4: "the unmatched-finding report prints severity and reason". Order: this must land AFTER the Finding.reason/RuleReport change (N1) or it will force corpus authors to suppress Unresolved. |
| ~KCJ0F5T markers | Add the marker words `advisory` and `unresolved` with optional `[reason]` and `required`; column/message apply to them; FORMAT.md documents. Acceptance: a failing self-test per mismatch kind includes "expected unresolved, got error" and "reason differs". |
| ~V88AAXW sections, multi-file | Multi-file cases are the vehicle for the cross-language matrix and for opaque-neighbour cases (a `.rs` with a sibling `.json`). Add acceptance: "a case may mix languages: one block per file with its own `fidelity=`, and the assertion applies to the union". The toml config block gains a `[mdtest]` table with `languages = [...]` matrix selection. |
| ~V6ZFY72 inline snapshots | Update mode must not silently change the outcome class of a snapshot (Fire/Clean/Unresolved/NotApplicable): require `FROB_MDTEST_UPDATE=1 FROB_MDTEST_ALLOW_CLASS_CHANGE=1` for a class change. Snapshot must include the reason code and remedy line for Unresolved. |
| ~14C4ZGJ render fix diff | Also render the Unresolved block: reason code in words and remedy (DG section 5 last row), so snapshots assert them; assert JSON carries `reason`. |
| ~G4WAFJT fix harness | Invariants reworded (3.3): parse status never degrades, opaque/hole count never increases, an outcome Fire->Unresolved after a fix fails, Unresolved is not "a remaining fixable finding". Self-test: a fix that wraps code in a macro (turning a Fire into an opaque phase) fails. |
| ~D3ZK8NM rule declarations | Acceptance 3 add: doc section "When it cannot decide" (what Unresolved looks like and the remedy); the Example block is executed with `expect` kinds fire / clean / unresolved; registry test fails a Universal rule lacking the notapplicable/unresolved example; derive refuses `needs` absent for a Universal rule (see N4). Acceptance 1 stays. |
| ~BGB8V55 (done) follow-ups ~C5DQ4WJ, ~QSK0WB1 | Their allowlist entries become (rule, required-case-kind) pairs, not just rule, so each rule's missing Unresolved/NotApplicable/vacuous cases are listed and shrink-only. Do not close these umbrellas on "fire+clean" alone. |
| ~MJG5PAQ unknown directives | Also make a `expect=` value other than fire|clean|unresolved|notapplicable an error with the allowed set listed; `rule=` without `expect=` is an error (already stated). |
| ~SASXGW5 panics | Add: a rule that panics on adapter garbage input is a failed case; add a per-adapter "garbage and unsupported input" case class asserting Unresolved or NotApplicable, never a panic (UM 3.2). |
| ~16NRSVC failure UX | Failure output prints expected class, actual class, subjects examined/total and the reason code (the `diff()` table in run.rs:165-190 currently prints severity and rule only). |
| ~T7EH2BG message convention | Separate rule for Unresolved messages (3.5); assert each Unresolved snapshot has a reason code and a remedy line. |
| ~VB2EYG6 GRL example runner (blocked, not in brief) | Do not build a separate runner: make GRL example blocks a front end to the gob-mdtest outcome vocabulary (one parser for `unresolved`/`notapplicable`/`known-gap`/`fixed`), or D103's "mdtest is primary" and GRL 9 fork permanently. |
| ~BP7TEN3 plan executor outcomes (blocked) | Its acceptance 1 (P+ via May -> Unresolved; P- absent even on May -> fire) is the same table as gob-ir/tests/eval.rs; require that both executors produce `RuleReport` and run the same polarity-conformance corpus. |
| ~8HJZ9MP tier-4 adapter packs | Generalise acceptance 2 ("reported at measured fidelity, not claimed") to ALL adapters via N6; this ticket then consumes the shared harness. |
| ~01ENJEW C# fixtures | Add: C# row cells asserted by the generated per-adapter matrix snapshot (N6) and the universal-rule x C# cells from N5; C# is F1, so its expected rows are mostly Unresolved/NotApplicable and are the first real exercise of F1. |
| ~2HHBFSY docs (four required cases) | Unchanged; also mention in UM 4.2 that tests assert required status (this audit's wording below). |

### 5.3 New tickets (one paragraph each)

N1. gob-rules: a typed Unresolved reason and a RuleReport on the test path. `gob_rules::Finding` has no
`reason` and no `subjects_examined` although UM 8 and RU 2 say it does, so reason codes live in message text
(`[sys-unresolved/<code>]` in grimble-bind/src/types.rs:175; `annotation-required:` prefix in gob-check/src/
required.rs:12; five separate reason enums: grimble-bind::Reason, gob-languages::UnresolvedReason,
gob-ir::PoisonReason, gob-symbols::GapReason, strings in program.rs). Add `Finding.reason: Option<
UnresolvedReason>` (closed enum for the UM 4.6 table plus `Opaque(String)`, `Hole`, `EdgeMay`, `EdgeUnknown`,
`Vacuous`, `Fidelity`, `ParseFailed`, `Partial`), a `RuleReport {rule, subjects_total, subjects_examined,
not_applicable, findings}` in gob-rules that gob-ir's `RuleOutcome` and gob-check's per-rule subject counters
convert into, migrate the three producers (gob-ir eval, gob-check status/required, grimble-bind) and delete
the message-prefix parsers. Acceptance: no production code parses a reason out of a message; a JSON schema
snapshot shows `reason`; mdtest `Runner` can return `RuleReport`. Blocks N2 and ~1X6M6MS.

N2. gob-mdtest: outcome classes `unresolved` and `notapplicable`, subject accounting and certified clean.
Implement section 5.1: `expect=unresolved|notapplicable`, markers `advisory:`/`unresolved[reason]:`/`required`,
`subjects=`/`subjects>=` (default `>=1` for clean), `fidelity=`, `parse=`, spanless header assertions, and the
`known-gap` and `fixed` modifiers shared with GRL 9. Migrate inv002.md:25 and add Unresolved blocks to cov001.md
(May-edge reach, partial parse, zero test-capable files), doc001.md, todo001.md (opaque text file), ref001.md.
Acceptance: self-tests where (a) a rule that examines nothing fails an `expect=clean` block, (b) an
Unresolved-only result fails `expect=fire`, (c) an Error result fails `expect=unresolved`, (d) a wrong reason
code fails, (e) a NotApplicable result fails `expect=clean` and passes `expect=notapplicable`. FORMAT.md and
BTC section 2 updated. Depends on N1; supersedes the hand-rolled assertions in frob-check/tests/fidelity.rs
(keep that file as the end-to-end check, delete duplicated cases).

N3. gob-mdtest: polarity- and tier-aware coverage meta-test. coverage.rs must read `RuleMeta.polarity`,
`tier` and `must_measure` and require the case kinds of the table in 5.1 per rule, per product, with the
allowlist keyed by (product, rule, case-kind) and still shrink-only; also require that the fire and clean
blocks of one rule live in ONE suite file (today a fire in crates/a and a clean in crates/b satisfy it) and
that the clean block certifies subjects>=1. Acceptance: removing COV001's Unresolved block makes the test fail
naming `COV001 P- unresolved`; a Universal rule without a notapplicable/unresolved block fails naming it; the
allowlist entries are split from ~C5DQ4WJ/~QSK0WB1 into per-kind lines each with a ticket.

N4. Rule metadata: `needs` and `min_fidelity` on the derive, delete `gob_check::need_of`. RU 2 requires
`needs(Q::...)` and UM 8 says the framework "decides applicability per file", but RuleMeta has neither and
`need_of` (gob-check/src/status.rs:66-76) is a string-keyed table the docs admit is a workaround
(fidelity.md last paragraph of the first section). Add `needs: &'static [Query]` and `min_fidelity` to the derive and
`RuleMeta` (compile error when absent for a Universal rule, in ~D3ZK8NM's trybuild set), derive
`subject_status_for` from them, and generate docs/reference/fidelity.md's rule columns from the registry so
the hand-written table cannot drift. Acceptance: no string rule id in gob-check/src/status.rs; fidelity.md is
generated and checked by `cargo dev gen --check`.

N5. Universal-rule language matrix. For every `tier = Universal` rule, an mdtest section per language of a
required set, taken from the registry: {rust (F3), python (F2), typescript (F2), csharp (F1), markdown (F4),
an F0 text file with no adapter, a binary file, an embedded-opaque island} with an expected class per cell
derived from `needs` x adapter capability (a mismatch between the derived expectation and the written
`expect=` is a test failure, so the matrix cannot be satisfied by copy-paste). Seed the expected cells from
LR section 6/7 and UM 6.1. Each cell is fire, clean, unresolved or notapplicable; a language still F0 gets
`unresolved reason=fidelity` (see N8). Coverage test (N3) requires the rows; a shrink-only allowlist lists
missing cells with tickets. Includes "parity cases": the same logical shape rendered in 3 languages with one
expectation, so a universal rule's semantics are proven the same across adapters.

N6. Measured fidelity and capability-matrix snapshots for every adapter. Replace `assert_eq!(Adapter.fidelity(),
F3)` (gob-symbols/tests/corpus.rs:157-178) with a harness that DERIVES the level from the corpus per UM 3.3
(F1 units+containment present; F2 Must lexical edges present; F3 apply edges with declared status; F4 attrs,
comments bound, regions, phases) and fails when claimed > measured and also when measured > claimed (stale
claim), reports the cells per `Implemented | NotApplicable(reason) | Gap(ticket)`, snapshots the matrix for
every registered language (today only web_corpus.rs) and generates `frob doctor --languages` and the README
table from the same data (UM 9 q3). Add an F0 adapter case (UM 3.2: one opaque node, every query Unknown) and a
garbage-input case per adapter asserting no panic and Unresolved/NotApplicable. Acceptance: promoting C# from
F1 to F2 without a Must-edge corpus case fails; dropping a Rust operator case fails.

N7. Polarity-conformance corpus run against every shipped rule. gob-ir/tests/eval.rs proves the polarity table
for the evaluator; no shipped rule is built on it (cov.rs hand-rolls May/poison logic; `RuleProgram` has no
non-test user). Add one standard small repository per polarity (a May-only edge, a Must edge, an opaque
region, an Unknown-visibility item) and require each rule's mdtest to contain the three polarity-implied
outcomes (the fire/clean/unresolved of 5.1) so that "rule behaves as its declared polarity says" is a test and
not a doc claim; fail when a P- rule fires on a May-only reach (a wrong Fire is the failure U rules out;
Theorem 3(b) "never emits an Error or Warn whose premise is false"). Where practical, port COV001 onto
`RuleProgram` and delete the hand-rolled path, which removes the divergence.

N8. Decision and fix: "no adapter yet" is Unknown, not NotApplicable (section 4.1). Record a decision,
update UM 4.1 glossary and 3.3, and either (a) change `subject_status_for` so an adapter-less TEXT file yields
Unresolved(reason=fidelity F0) for capability rules (consistent with UM 6 "worst case is F0 with everything
Unresolved" and with README claims) with a rolled-up one-per-rule-and-language form so it is not noisy, keeping
NotApplicable for binary files and declared-featureless languages; or (b) amend UM 3.3/6 to say F0 text is
NotApplicable for capability rules and justify why that is not a silent pass. Update fidelity.md, fidelity.rs
and the N5 matrix accordingly. Owner decision needed on the noise tradeoff (a), but this is the pivot of the
whole NotApplicable/Unknown distinction the tests are meant to protect.

N9. Lexical-on-opaque corpus. UM 2.2 item 4 says text/literals/prose queries read opaque payloads, so lexical
rules (CI007 over a shell `run:` body, DK004, secrets, PATH001) fire inside opaque regions while structural
rules over the same region are Unresolved. No test anywhere exercises both halves. Add an mdtest section type
(`opaque-region`) with two blocks per lexical rule: Fire inside an opaque island (shell string in YAML, a
`#if 0` block, a template literal) and an Unresolved for a structural rule over the same island; the
registry marks a rule lexical when `needs` is only Q03/Q11/Q14 (depends on N4).

N10. Ecosystem and adversarial corpora count examined subjects. Extend ~9HS3VP7 so the report adds
`files_examined/files` and `subjects_examined` per rule per language and fails the PR comment on a regression
(a drop reads as an improvement in a pure finding diff, 3.8), and include one F0-heavy repository (Go or Ruby
plus YAML plus shell) so opaque handling is exercised outside hand-written fixtures. Non-blocking comment stays;
the "subjects examined dropped" line becomes blocking in the nightly.

### 5.4 Design-doc text that should change (quote, then proposal; none edited)

1. build-test-ci.md section 2, the sentence "(the fire-and-clean controls and the shrink-only coverage
   allowlist are frob additions that neither ruff nor ty has)" and the table row for markdown corpora ("then
   expected findings or expected symbols/edges; ... a fenced block without `expect=` is documentation").
   Propose: "A case has one of four expected outcome classes, fire, clean, unresolved or notapplicable, taken
   from GRL section 9. A clean case certifies that the rule examined at least one subject (UM 4.2); the
   absence of a finding is never a pass by itself. Every rule has a fire, a clean and, per its polarity and
   tier, the unresolved, notapplicable and vacuous cases of the table in testing.md." (Create one home for
   the table rather than restating it here.)

2. build-test-ci.md section 2, the D103 paragraph, "strict inline markers (rule, severity, line, optional
   column and message)". Propose: "strict inline markers (rule, severity in {error, warn, advisory,
   unresolved[reason]}, location, optional column and message). Strictness counts Unresolved and Advisory
   findings; a rolled-up Unresolved is asserted by a header expectation."

3. build-test-ci.md section 2, "The runner applies ruff's fix invariants ... (fixpoint within 10 rounds,
   reparse, no new parse error, no fixable finding left)". Propose: "... (fixpoint within 10 rounds, reparse
   with parse status and opaque/hole count not degrading, no fixable finding left, and no finding changing
   class from fire to unresolved)."

4. build-test-ci.md section 2, rule-docs row: "every rule's doc example runs as an mdtest (ty lint_docs
   pattern)". Propose adding: "The rule page has a fourth section, When it cannot decide, whose example is an
   `unresolved` case; a Universal rule's page also shows its per-language row (applicable, unresolved,
   notapplicable)."

5. rules.md section 2, "a generated mdtest with one firing and one non-firing case plus, for a universal rule,
   a third fixture in a language that lacks the feature, expecting Unresolved or a not-applicable listing and
   never clean". This is false today (gob-macros generates nothing). Either state "generated" ->
   "required by the coverage test (N3) and written by hand or scaffolded by `cargo dev new-rule`
   (~0H3WYTR)", or build the generation. Do not leave a doc sentence that no code satisfies.

6. universal-model.md section 3.3, "adapters are graded and the grade is checked by a corpus per language
   (gob-mdtest): for each universal operator the adapter claims, a sample and the expected U term plus scope
   graph." The corpus is not in gob-mdtest (it is gob-symbols/tests/corpus.rs, insta) and it does not check the
   grade. Propose: "adapters are graded by a corpus per language (gob-symbols/tests/corpus and the generated
   capability-matrix snapshot); the level is DERIVED from the corpus (F1 ... F4 as listed) and the test fails
   when the declared level differs from the measured one in either direction."

7. universal-model.md section 4.2, after the "The gate" paragraph, add: "Testing. A rule test asserts one of
   four outcome classes per case (fire, clean, unresolved, notapplicable) and the subject accounting of the
   outcome; clean means certified over at least one examined subject. For each rule, tests exist for every
   outcome its polarity can produce and, for a universal rule, for each language fidelity class (rules.md
   section 2, build-test-ci.md section 2)."

8. universal-model.md section 4.1 glossary and section 3.3, depending on the N8 decision: state explicitly
   whether an artifact with no adapter yet is Unknown (Unresolved) or NotApplicable for capability rules; the
   current text says Unresolved (3.3 last sentence, 6 intro) and the shipped tool says NotApplicable.

9. code-model.md section 3, "(each adapter ships fixtures/*.{ext} with expected symbols, digests, U terms,
   imports: the fidelity corpus of universal-model.md 3.3)". Add: "Each adapter also ships: a garbage-input
   case (no panic, Unresolved or NotApplicable), a partial-parse case (PARSE002 and the hole caveat), and, for
   every universal rule, the expected outcome class for this language (testing.md matrix), generated from the
   capability cells."

10. docs/design/README.md D103 row, last clause: "frob keeps its fire-and-clean controls and shrink-only
    coverage allowlist". Add: "and extends the outcome vocabulary to unresolved and notapplicable with subject
    accounting (universal-model.md 4.2), so that D103's two-valued ty/ruff model does not hide silent
    passes".

11. rules.md section 8 last paragraph: "Markdown-driven cases (`tests/cases/*.md`: a fenced repo, then expected
    findings) are the primary test form". The directory is `tests/mdtest/` and the form is FORMAT.md
    (already noted in RT row 15, ~NEW-10, still not fixed in the doc); also "expected findings" should read
    "expected outcomes".

12. grl-spec.md section 9 and ~VB2EYG6: replace the standalone marker syntax (`//~ warn`, `//~ unresolved`) with
    a pointer to the shared gob-mdtest grammar, or state that gob-mdtest is a front-end implemented over the
    same crate, so the project has one example grammar.

## 6. Priority order (smallest set that makes U testable)

1. N1 (typed reason + RuleReport) then ~1X6M6MS/~KCJ0F5T with the extended marker words: otherwise strict mode
   (a D103 deliverable) actively harms U (3.1).
2. N2 (outcome classes, certified clean) and N8 (decide NotApplicable vs Unknown for adapter-less text).
3. N3 + N4 (polarity/tier-aware coverage, needs on RuleMeta) so the missing cases are enumerated and shrink-only.
4. N6 (measured fidelity, matrix snapshots), N5 (language matrix), N7 (polarity conformance), N9, N10.
5. The doc edits in 5.4 in the same changes as their code (frob rule: docs change with code).

## 7. Things I looked for and did not find

- Any mdtest block that asserts Unresolved with a reason, a subject count, a NotApplicable or a non-Rust
  production language (only grimble-bind's own corpus asserts reasons and subjects, in a separate format).
- A derive-generated mdtest or third fixture (gob-macros/src has no mention of mdtest or fixtures).
- A `needs` field on `RuleMeta` (absent; `Polarity` and `must_measure` are present, `tier` is present).
- A test that an adapter's declared fidelity equals its measured fidelity (only constants and operator-claim
  coverage).
- Any statement in rule-testing.md or codegen-macros.md about Unresolved, subjects or polarity (none).
- Verification of UM's external citations (Rice, Wells, Immerman/Vardi): out of scope, UM open question 4 stands.
