# Formal review: the universal structural model U and GRL (2026-10-08)

Referee: programming-languages and logic review, read-only. Repository
state: branch `experimental` at 71dc268c8, clean tree. Inputs read:
docs/design/universal-model.md, grl-spec.md, rule-authoring.md,
testing.md, language-engines.md; notes/research/calculi.md (sections
4.10, 6.4, 8), rule-languages.md, paradigms.md, reading-list.md (by
heading); crates gob-ir, gob-plan, gob-caps, gob-rules, gob-check
(applicability), the rule declarations in every rule crate, and the
staged draft scratchpad/staged/cohesion.md (D118-D121; section 5 below).
Every literature claim has a fetched URL in section 7. Anything I could
not fetch is marked [unsourced].

## 0. Verdict in one paragraph

The design is grounded in the right literature. The literature is
sorted ABTs, scope graphs, Kleene three-valued logic, may/must
abstraction, and Datalog and descriptive complexity, and these are the
standard tools for this problem. TVLA (Sagiv, Reps and Wilhelm 2002) is
the closest prior art for "Kleene logic over an abstraction, with
definite answers sound", and the spec does not cite it. The formal
claims, though, are stated more strongly than they are proved, and the
implementation delivers almost none of the claimed machinery to
production rules:

- No production rule runs through GRL.
- No production rule runs through the gob-ir Kleene evaluator
  (`RuleProgram`).
- Every shipped rule is hand-written Rust: over gob-symbols'
  `SymbolGraph`, over side inputs, over bound-tool output, or (two
  families) over gob-ir query functions directly.

The theorems have four real gaps:

1. Theorem 2's proof does not cover fixpoints, and the semantics it
   implies makes the closed fragment inexact.
2. "FO+LFP, equivalently stratified Datalog" is false (Kolaitis 1991).
3. The polarity table's "holds on Must facts" reading is unsound in the
   presence of negation.
4. NotApplicable is used as a fourth truth value with no connective
   semantics.

The code has one soundness bug of the kind the theorems forbid: an
Unknown resolution is read as "no edge", so P- and Pc rules can certify
or fire wrongly. GRL also has a semantic dangling-filter ambiguity that
changes the meaning of `no` (the generator ticket ~K0FVJFM covers half
of it). None of this is fatal. Restating U as stratified Datalog over
lo/hi relation pairs fixes the theory. That is the well-founded
semantics restricted to this fragment, which coincides with the
two-pass evaluation `Relation::closure` already does. GRL then gets a
denotation into that, plus property tests that try to falsify the
theorems.

## 1. State of the machinery, measured

### 1.1 U (crates/gob-ir, 10.3 kLOC including tests)

| Spec item | Status | Evidence |
|---|---|---|
| ABT terms over Sigma_U + Sigma_L (2.1, 2.3) | Implemented. Arena terms, 13 universal operators plus adapter ops, binders with valence-aware scoping (`binds_over`), alpha-normal printer. Sorts are NOT checked: `arity_check` checks only the child count. `attr`'s valence `(target; payload)` is implemented as "child of target", which differs from the table. | gob-ir/src/term.rs:186-210, operator.rs; tests/properties.rs (alpha-equivalence, digest determinism, trivia exclusion: proptest) |
| Identities, symrefs (2.2, 2.6) | Implemented and tested (round-trip proptest) | symref.rs, tests/properties.rs:232 |
| Scope graph with Must/May/Unknown (2.2 item 3) | Implemented: resolution with label order, shadowing, opaque `may_define`/`may_read_scope` hints, memoised. Every adapter builds it with `ScopeGraph::from_term`, the purely lexical view, all edges Must, no import edges. Cross-file resolution with status lives in a SECOND model, gob-symbols' `SymbolGraph`, which is what rules read. | scope.rs:435-620; gob-symbols/src/{rust,python,csharp,yaml,markdown,html/mod}.rs all call `ScopeGraph::from_term` |
| Locations, non-byte addresses (2.5) | Implemented and tested (grid, notebook corpora) | location.rs, tests/corpus/{grid,notebook}.rs |
| Answer type, Kleene Truth (4.1) | Implemented. `Answer` has 4 constructors, but no order or lattice operations are defined on it. `Truth` is K3 with min/max. | answer.rs |
| Polarity and subject accounting (4.2) | Implemented in `RuleProgram::evaluate`, unit-tested per polarity | eval/program.rs; tests/eval.rs (747 lines) |
| FO+LFP evaluator (8, "the FO+LFP evaluator") | NOT a formula evaluator. Rules are Rust closures (`StratumFn`, `CheckFn`) over `Ctx` accessors that record "poison". The only fixpoint is `Relation::closure` (two reachabilities: Yes-only and any). There is no Datalog front end, no semi-naive evaluation, and no negation operator: negation is whatever the closure computes. | eval/mod.rs:1-9 says so; eval/relation.rs:114-140 |
| Facet digests, scheme 2 (7.1) | Implemented, golden and property tested | digest.rs, print.rs |
| Web-engine queries Q48-Q51 | Implemented (markup, style, const_value with budget and external refs) | markup.rs, style.rs, const_value.rs (866 lines), tests/web.rs |
| Fidelity measured by corpus (3.3; testing.md 5) | NOT implemented. Each adapter hard-codes `file.fidelity = F2/F3/...`, and the gob-caps MATRIX is hand-written. No test compares a declared level with a measured one. | gob-symbols/src/python.rs:376, rust.rs:469, ...; gob-caps/src/matrix.rs:44-57 |

Consumers of the evaluator: `RuleProgram`, `Ctx` and `Observation`
appear in no crate outside gob-ir (grep over crates/). Two production
rule families read U data directly in Rust:

- COLOR001 reads `gob_ir::style`.
- The grimble SYS rules read `gob_ir::select` owner selection.

### 1.2 GRL (crates/gob-plan, 11.1 kLOC including tests)

| Stage | Status | Evidence |
|---|---|---|
| Lexer | Done, tested | grl/lexer.rs, tests/lex.rs |
| Parser | Done, recovering, with malformed-input tests and a property test | grl/parse/*, parse/tests/{props,malformed}.rs |
| Printer | Done. The round-trip generator found two ambiguities (~K0FVJFM, open), which the printer works around with parentheses. | grl/print.rs, tests/print_stability.rs (1150 lines) |
| Error goldens GRL001-016 | Cases exist for some codes (GRL001, 002, 004-007, 009, 010, 012, 014) | tests/grl_errors/cases/*.grl |
| Name and type checking against the catalog | Only inside exec.rs, only for web kinds. The catalog lists 5 web kinds; the core kinds (`function`, `call`, `test`, `comment`, ...) are absent. | catalog.rs:1-10 ("the core kinds join as their adapters land") |
| Planner, plan IR, validation, codec | Plan IR, validator and codec exist. No compiler from AST to plan IR, no planner. | plan/{ir,validate,codec}.rs |
| Executor | `exec.rs` (451 lines): a single `find` over `element`/`attribute`, `not/and/or`, `==`/`!=`, flags, and `has attribute(...)`. It IGNORES every header (polarity, lang, severity, needs, must_measure), runs no examples, and has no subject accounting. It is used by one test (tests/web_rule.rs) and no product. | exec.rs:267-330, 419-450 |
| Codegen of std rules into the binary | Not started | - |
| `rule test/why/check/catalog/fmt` verbs | Not implemented | - |

### 1.3 Rules by kind (52 `#[rule(...)]` declarations, all on the legacy derive)

The D107 attribute with `applies =` is used only by test fixtures:
gob-check/tests/product_rules/*/src/rules/*.rs and
gob-rules/tests/rule_attr/todo001.rs. `temporary_applies`
(gob-check/src/applicability.rs:210-222) supplies `applies` for 12
legacy ids. Counting by what the evaluation actually reads:

| Kind | Count | Ids (file) |
|---|---|---|
| Universal, over U, through GRL or `RuleProgram` | **0** | - |
| Per-language, over U, through GRL or `RuleProgram` | **0** | - |
| Per-language, hand-written Rust reading gob-ir queries | 1 (+ part of 12) | COLOR001 (crunk-check/src/rules/color001.rs, `gob_ir::style`); SYS001-011, SYS013 (grimble-bind/src/rule_defs.rs), whose evaluation in grimble-bind/src/rules.rs mixes `gob_ir::select` with gob-symbols |
| Universal-tagged, hand-written over gob-symbols `SymbolGraph`/`SymbolRecord` | 12 | COV001, COV003, DOC001, INV001, INV002, EXC001/003/005/007 (frob-obligations), DRIFT001-004, AFFECT001 (frob-ack), TEST001 (frob-tests). COV001 computes Must and May reach over `SymbolGraph` (frob-obligations/src/cov.rs:303-304), not over U. |
| Universal-tagged, hand-written text scanning (no U, no gob-symbols) | 6 | TODO001/TODO002 (per-language comment scanner frob-obligations/src/comments.rs, not U `comment` nodes), REF001, DOC002, DSL001/002, PARSE001 (gob-directives) |
| Bound-tool stage rules (external tool output) | 6 + 2 | CI001/003/006/007/010/014 (zizmor and actionlint parsers, gob-check/src/tool_parse.rs), TOOL001/002 |
| Non-code (ledger, PM, release, lease, config, model language, perf, sibling) | 21 + 21 | TICK001-005, PM001/002/013/033/034, REL001-003, SCOPE001, CFG001, PERF001, READ001, PROC001, SIB001; MDL000-021 (grimble-model/src/rule_defs.rs, over the .grmb AST) |

The legacy `tier = Universal` label is on 49 of 52 declarations. It
includes the ledger, release and PM rules, so the label carries no
information about U. The D107 resolver `gob_check::applicability::resolve`
exists, but see M3: it ignores capability cells for every parsed file.

### 1.4 What per-language structural lints still need

In dependency order:

1. **Core catalog kinds bound to U.** `function`, `call`, `comment`,
   `test`, `stmt`, `branch`, `loop`, edge verbs. Today the catalog has
   web kinds only.
2. **One resolution model.** Rules read `SymbolGraph`; U's scope graph
   is lexical-only. Until import and call resolution with status is
   lowered into U (or `SymbolGraph` is exposed as U relations with
   lo/hi), a GRL `calls` verb has nothing sound to read.
3. **Snippets and `as KIND` over gob-pattern.** The grammar parses
   snippets (grl/snippet.rs). There is no matcher, no `as roles` lifting
   (Q46), no metavariable binding, and no GRL002 parse-tree display.
4. **Capability gating.** GRL's `needs` still means side relations
   (grl/parse/rule.rs:302). D107 renamed that to `reads` and made
   `needs` the capability list. A GRL rule therefore cannot declare
   capabilities today, so the "1:1 with `applies`" claim of
   rule-authoring.md section 2 does not hold.
5. **The applicability resolver must read the matrix for parsed files**
   (M3).
6. **A compiler from AST to plan IR, polarity-aware executor and
   subject accounting**: either reuse `RuleProgram`'s `interpret`, or
   better, replace both with the semantics of section 2.6.
7. **`rule test`**, so GRL examples are run (D106 outcome classes).

## 2. Soundness of the formal claims

Severity tags follow the auditor scale: HIGH means a wrong definite
answer is possible, MEDIUM a real gap with a bounded trigger, LOW an
imprecision.

### 2.1 Theorem 1 (totality): true, trivially; three imprecisions (LOW)

- The quantifier "for every language L that has a computable parser" is
  unnecessary. The constant F0 adapter makes the statement hold for
  every artifact, and parse_L "total by requirement" is an assumption,
  not a consequence of L having a parser: real parsers are partial on
  bytes. Restate it as: "for every adapter (parse_L total, rho_L with
  opaque default, bind_L total), T_L is total".
- "At most one U node per concrete node" and "linear time" are false
  once `phase` expansion within a budget, or adapter lowering that
  synthesises nodes (the `lit(tag)` head of markup elements), is
  allowed. The bound is (budget + c) * |tree|, which is still linear for
  a fixed budget; say so.
- Building the scope graph is linear. Resolving it is not part of T_L
  and is not linear with imports (the scheduling problem of Statix:
  Rouvoet et al. 2020, van Antwerpen et al. 2018). Theorem 1 should not
  be read as bounding resolution.
- "Sorted" is not enforced. The initial-algebra argument (Goguen et al.
  1977) gives compositionality for the unsorted free algebra too, so
  nothing breaks, but either check sorts in `TermBuilder::node` or drop
  "sorted".

### 2.2 Theorem 2 (adequacy): the statement is too strong; the proof misses fixpoints (HIGH as a spec defect)

1. **"FO with least fixpoints (equivalently stratified Datalog)" is
   false.** Stratified Datalog is strictly less expressive than FO+LFP
   on finite structures (Kolaitis 1991, "The expressive power of
   stratified logic programs"). FO+LFP coincides with inflationary
   Datalog, not stratified Datalog. Pick one. GRL needs much less than
   either (2.5), so the right statement is about the smaller class.
2. **The class is all of PTIME.** U-structures carry a total location
   order within an artifact, and paths can order artifacts. On ordered
   finite structures, FO+LFP captures exactly PTIME (Immerman 1986;
   Vardi 1982). "Every predicate in the class is polynomial" is
   therefore the capture theorem, and adequacy says only that every
   polynomial query is expressible. That is fine, but the content of
   Theorem 2 is the soundness and exactness clause, and that is where
   the proof is weakest.
3. **The proof is by induction on the formula and does not handle LFP.**
   A least-fixpoint subformula is not a structural subterm. The research
   note's version (calculi.md, Theorem "structural coverage", proof (1))
   is better: it uses monotonicity of the Kleene connectives in the
   information order and takes the least fixpoint in that order. That is
   Fitting's Kripke-Kleene semantics (Fitting 1985). The spec dropped
   the argument.
4. **The information-order fixpoint makes the closed fragment inexact.**
   Counterexample. The closed fragment has no opaque, no hole, no May
   edges; take `edge(a,b), edge(b,a)` and
   `reach(x,y) <- edge(x,y) or exists z. edge(x,z) and reach(z,y)`, and
   ask `reach(a,c)`. Classically it is No. In the Kripke-Kleene fixpoint
   it stays Unknown, because the loop a-b-a is unfounded and starts at
   bottom = Unknown. So "on the closed fragment it is exact" fails under
   the semantics the note proposes. The fix is to evaluate recursion
   classically on each bound:
   - lo = lfp over Must facts;
   - hi = lfp over Must plus May facts;
   - answer Yes if the tuple is in lo, No if it is not in hi, Unknown
     otherwise.

   For positive recursion with stratified negation, where negation
   swaps lo and hi, this equals the well-founded model (Van Gelder,
   Ross and Schlipf 1991). The well-founded model coincides with the
   perfect model on stratified programs (Apt, Blair and Walker 1988;
   Przymusinski 1990). `Relation::closure` (eval/relation.rs:114-140)
   already does exactly this two-pass computation, so the code is right
   and the spec's argument is not.
5. **Hidden closed-world hypothesis.** "An atom that touches opaque, hole
   or non-Must is Unknown" does not cover the absence of an atom. A
   negative literal `not edge(f,g)` is No or Yes depending on whether
   the pair is stored, and it is sound only if every relation is given
   as a pair R_lo <= R_true <= R_hi with R_hi complete. The theorem must
   state this as a hypothesis on adapters: "May sets are
   over-approximations" (4.4 says this for May, but Unknown resolutions
   have no R_hi at all). Code consequence: H1.
6. **"Preserved and reflected by T_L" needs more than rho_L being a
   morphism.** Reflection about the SOURCE needs rho_L to be faithful
   on every distinction the formula reads (two source kinds mapped to
   one operator are indistinguishable). Restate exactness as a statement
   about U, plus a per-adapter faithfulness obligation discharged by the
   conformance corpus. Theorem 3 already admits this for bind_L.
7. **Aggregates and quantifiers are not covered.** The proof says
   nothing about `count`, or about quantification over a domain that is
   itself Bounds (an opaque region may hide members). The sound
   definitions:
   - `some x in D. phi` = OR over x in D_hi of (mem_D(x) AND phi(x)),
     OR'd with Unknown if D may have members outside D_hi (an opaque
     region in scope);
   - `count` = the interval [#{x : value Yes}, #{x : value not No}];
   - comparisons by interval, so `count == k` is Yes iff lo = hi = k,
     No iff k is outside [lo, hi].

   Evaluating a non-monotone predicate at the endpoints is unsound.
   Counterexample: "count is even" with lo = {a}, hi = {a, b, c} is
   "odd" at both endpoints, but {a, b} is even. Ross and Sagiv (1992)
   is the reference for when aggregation is monotone.

### 2.3 The polarity tables: "on Must facts" is unsound with negation (HIGH)

grl-spec.md 7.2 and universal-model.md 4.2 define P+ as "fires when the
bad pattern holds on Must facts; clean when it fails even on May facts".
That reading substitutes one edge set for the whole formula, which is
correct only for formulas with no negation.

Counterexample (P+):
`find f: function where not f has attr "frob:shell" and not some t: test where t calls f`,
where the only test call is a May edge. On Must facts, `t calls f` is
false, so `not some t ...` is true and the rule fires an Error. The
correct K3 value is `not Unknown = Unknown`, which gives Unresolved.

The right definition is short. Evaluate the formula once in K3, with
May atoms Unknown, then map the result:

| Polarity | Yes | Unknown | No |
|---|---|---|---|
| P+ | fire | Unresolved | clean |
| P- (formula describes the good thing) | clean | Unresolved | fire |

P0, Pn and Pc are special cases (Pn is the interval comparison of
2.2.7; Pc is the lo/hi closure). Equivalently: evaluate positive
occurrences on lo and negative occurrences on hi, which is the standard
polarity-aware substitution. The `RuleProgram` code sidesteps the issue
because checks build `Observation::Set(Bounds)` by hand. A GRL executor
built from the table as written would not.

Related (MEDIUM): `certainly` and `possibly` (grl-spec 7.2, plan
`Certainty`) are the K3 "definitely" and "possibly" operators. They map
Unknown to No and to Yes respectively, so they are NOT monotone in the
information order, which breaks the lemma Theorems 2 and 3 rest on.
`not certainly f calls log` is Yes on a May edge, and a P+ rule built on
it fires on a false premise. Restrict them to positive positions, or
define them as producing Unresolved-free predicates whose message must
say "possibly".

### 2.4 Theorem 3 (honesty)

- (a) Rice is stated about "U itself", but U "is not a semantics"
  (universal-model.md lines 36-40, 2.4). Rice's theorem (Rice 1953) is
  about the partial functions programs denote. The correct statement is
  about a Turing-complete source language L: any nontrivial semantic
  property of L-programs is undecidable, and since T_L is computable, a
  query on T_L(p) deciding it would decide it on p. (LOW)
- (b) is valid only as "if every atom meets its contract and every
  connective is K3-monotone, then definite answers are sound". It does
  not apply to:
  - GRL's `certainly`/`possibly` (2.3);
  - GRL's `within N` (below);
  - `RuleProgram` closures, which can read `ctx.term()` and
    `ctx.model()` directly and bypass poison recording (ctx.rs public
    accessors), so soundness there is by convention.
- **`within N` versus honesty (HIGH, spec level).** grl-spec 12,
  COV001: `some t: test where t reaches f via calls within knob.depth`
  with P-. A test that reaches f at depth 13 > 12 gives No on every
  edge set, so the rule FIRES "has no test that reaches it", and the
  premise is false. A depth bound is a budget. Truncation must make the
  frontier Unknown (Unresolved `budget`), as plugins.md promises for
  budgets in general. Note that the production COV001
  (frob-obligations/src/cov.rs:101-110) uses unbounded reach, so
  rewriting it in GRL as specified would introduce this bug.
- Kleene versus Belnap: see 2.7.

### 2.5 The GRL termination and PTIME claim (MEDIUM)

"No construct recurses ... every plan terminates in polynomial time" is
true for data complexity with a fixed rule, under assumptions the spec
does not state:

1. **`def` must be materialised, not inlined.** A chain
   `def d_i(x) = d_{i-1}(x) and d_{i-1}(x)` inlines to 2^i atoms.
   Evaluating defs as views keeps it polynomial.
2. **Engine relations must be PTIME.** `cell`, owner resolution,
   `resolves to`, `const_value` and unbounded Q30 `reaches` are outside
   GRL. Their cost is the engine's. `const_value` has a step budget;
   the others need one stated.
3. **Snippets with repeated sequence metavariables.** Matching a pattern
   with variables against a sequence is NP-complete in the pattern
   (Angluin 1980; Ehrenfeucht and Rozenberg 1979). It is polynomial
   (n^k for k sequence variables) for a fixed pattern only. Semgrep
   unifies repeated metavariables (fetched docs), and GRL 7.1 says a
   reused name is an equality test.
4. **Combined complexity.** For the FO core it is PSPACE-complete
   (Vardi 1982). With the plan validator's limits (MAX_VARS = 1024,
   MAX_DEPTH = 64; plan/limits.rs) a hostile pack plan is "polynomial"
   with exponent up to 1024. That is meaningless as a bound, so the
   runtime budget is the real guard.

   The printed `CostClass` (PerFile | PerRepo | Closure(d),
   plan/ir.rs:97-104) does not reflect the exponent. It should report
   the number of simultaneously live variables, or better the
   (fractional hypertree) width of the join. Joins are bounded by the
   AGM bound (Atserias, Grohe and Marx 2008), and acyclic joins are
   linear in input plus output (Beeri, Fagin, Maier and Yannakakis
   1983).

### 2.6 Which known fragment GRL is, and what that buys

GRL as specified is: non-recursive first-order logic over finite
relational structures, plus counting and arithmetic on counts (`count`,
`+ - *`), plus bounded transitive closure (`reaches ... within N`, which
is FO-definable for each fixed N), plus external oracle relations. In
database terms it is non-recursive Datalog with stratified negation and
aggregation, which is relational algebra with grouping and aggregates.

- Libkin (2003) shows such languages are local and cannot express
  reachability. That is a precise justification for keeping `reaches`
  as a built-in.
- Pure FO has AC0 data complexity, and FO with counting quantifiers
  over ordered structures is in uniform TC0 (Barrington, Immerman and
  Straubing 1990). Both are far below the "polynomial" the spec claims.
- Removing `within` gives FO+TC, which captures NL on ordered
  structures (Immerman 1987).
- Snippet matching without repeated metavariables is MSO-definable on
  trees, and MSO on trees equals tree automata (Thatcher and Wright
  1968; Doner 1970). That gives linear-time matching for a fixed
  pattern and is the formal reason tree-sitter-query and Semgrep-style
  patterns are cheap. Repeated metavariables need equality constraints
  between subtrees, which leave the regular class [unsourced: tree
  automata with equality constraints].

What this buys:

1. **Evaluation strategy.** Compile to relational algebra and run
   worst-case-optimal or Yannakakis joins. No fixpoint engine is needed
   for GRL itself, and semi-naive evaluation (Bancilhon 1986) is needed
   only inside the engine's closure relations.
2. **Incremental maintenance per file** for non-recursive views is
   standard [unsourced: DRed, Gupta, Mumick and Subrahmanian 1993].
3. **`rule why` as provenance.** Why-provenance over the semiring
   N[X] or Boolean polynomials (Green, Karvounarakis and Tannen 2007)
   is exactly "which atoms and edges made this binding fire". Provenance
   with a Must/May annotation is the principled replacement for the
   ad hoc poison list.
4. **A denotational semantics in one page**:
   [[rule]] : Structure_lohi -> (Bindings -> K3), defined
   compositionally, with the polarity map of 2.3 on top.

CodeQL's QL is the precedent: it compiles to Datalog and requires
monotone recursion (an even number of negations) (Avgustinov et al.
2016; CodeQL docs). Souffle (Jordan, Scholz and Subotic 2016) shows the
engine side.

### 2.7 Is K3 the right lattice?

K3 is the right lattice for verdicts. It is the information-order
completion of {Yes, No} that abstract interpretation produces from
may/must (Cousot and Cousot 1977, 1979). TVLA's embedding theorem
(Sagiv, Reps and Wilhelm 2002) is exactly "a definite K3 answer on the
abstraction holds in every concretisation", which is Theorem 3(b) done
properly. Cite and copy that proof structure. Three-valued model
checking (Bruns and Godefroid 1999) is the same idea for temporal
properties.

Two things K3 alone does not model:

1. **Conflict (Belnap's "Both").** The system has several sources for
   one fact:
   - U's lexical scope graph versus `SymbolGraph`;
   - a `frob:calls` directive versus resolution;
   - in D119, an annotation versus local inference (5.3).

   Belnap's FOUR (Belnap 1977) and bilattices (Ginsberg 1988; Fitting
   1991) represent "sources disagree" separately from "no source
   knows". The recommendation is not to expose FOUR to rule authors.
   Combine sources in the knowledge order (join), and collapse Both to
   Unknown for verdicts, which is sound. Keep the Both as a distinct
   Unresolved reason ("conflict: directive says X, resolution says Y"),
   so conflicts are surfaced and fixed rather than hidden as Unknown.
2. **NotApplicable is not a truth value (MEDIUM).** grl-spec 7.2 says
   every condition evaluates to "Yes, No, Unknown or NotApplicable
   (... Kleene connectives)". K3 has no fourth value. The only coherent
   reading is an infectious value: weak Kleene, or Bochvar's "nonsense"
   value (SEP, many-valued logic). Under that reading,
   `not d inside test` in a language with no test convention is NA, and
   the NOPE001-style rule silently vanishes for every subject in that
   language. Classically, `d inside test` is simply No there (there are
   no tests), so the rule should fire. Recommendation: make NA a
   property of a (rule, language) pair decided statically from `needs`
   and the matrix, never a value inside formulas. Inside a formula, a
   kind whose capability is NotApplicable denotes the empty set,
   exactly. P- rules that quantify over such a kind (COV001's `test`)
   are then excluded by their `needs`, which is the intended behaviour.
   The `exec.rs` and `Observation` code already treats NA per subject
   only, which is consistent with this.

Provenance (2.6 item 3) is the third axis, and it is orthogonal: a
provenance semiring annotated with K3 gives both the verdict and the
explanation.

### 2.8 Code findings against the theorems

**H1 (HIGH): an Unknown resolution is read as "no edge"; poison from
strata is discarded.**
- Where:
  - gob-ir/src/eval/ctx.rs:293-294: an `apply` whose head is not a
    `ref` is skipped with no poison;
  - ctx.rs:310 and :256: `Resolution::Unknown` records poison but
    inserts no pair;
  - eval/relation.rs:51: an absent pair is No;
  - ctx.rs:204-221: `holds` returns No for an absent pair unless an
    endpoint is opaque;
  - eval/program.rs:309: `ctx.clear_poison()` runs after the strata,
    so poison recorded while deriving `rel_calls` in a stratum is lost;
  - program.rs:651: `Reach` observations are trusted even when
    poisoned.
- What's wrong: universal-model.md 4.4 says "May sets must contain the
  true referents ... otherwise Unknown". An Unknown edge means "may go
  anywhere", and its contribution to R_hi must be top (an edge to every
  candidate, or a distinguished frontier that makes every reach query
  from that node Unknown). `resolve_name` returns Unknown whenever there
  are no candidates (scope.rs:438). That covers every imported or
  external name, because adapters build lexical-only scope graphs.
- Failure scenario (Pc): `f` calls `g` through an alias the adapter
  cannot resolve, and `g` calls `f`. `rel_calls().closure()` has no f-g
  pair, `reach.get(f, f)` is No, `hi` is false, and CYCLE certifies f
  "clean" with a cycle present. The `cycle_rule` test
  (tests/eval.rs:599-608) has the same shape.
- Failure scenario (P-, through strata, as in
  `strata_derive_relations_read_by_later_strata_and_checks`): a test
  calls `f` through a member-expression head. The pair is missing, the
  poison is cleared, `holds` returns No, and the P- rule fires
  "no test reaches f".
- Fix direction: give `Relation` an explicit `unknown_out: Set<NodeId>`
  (nodes with an Unknown or unclassified outgoing edge). In `closure`,
  any path through such a node makes every not-yet-Yes target from the
  source Unknown. Stop clearing poison after strata, or attach poison
  to the derived relation. Count head-not-a-ref applies as Unknown
  edges. Add the two scenarios above as tests.

**M1 (MEDIUM): GRL dangling filter changes the meaning of `no`.**
- Where: gob-plan/src/grl/parse/cond.rs:44-50 (`binding` greedily takes
  `where cond`, and `cond` greedily takes `and` and `or`).
- What's wrong: in `where A and no t: T where B and C`, `C` is parsed
  inside the `no`. When C does not mention t, `no t: T where (B and C)`
  is not equivalent to `(no t: T where B) and C`. The first is Yes
  whenever C is No, so a rule meant as "untested AND public" fires on
  non-public functions. ~K0FVJFM covers the newline-`where` form of the
  same problem, not the `and`/`or` continuation.
- Fix direction: require parentheses or braces around a quantifier body
  that is followed by a connective (`no t: T where { B } and C`), or
  end a quantifier body at the end of the line. Document the rule in
  grl-spec section 5 and have the printer's generator cover it.

**M2 (MEDIUM): the GRL executor ignores headers and accounting.**
- Where: gob-plan/src/exec.rs:267-330 and 419-450.
- What's wrong: polarity, lang, needs and must_measure are never read.
  A P- rule is run as P+. A rule over zero elements returns an empty
  `Outcome`, which is a silent clean. That contradicts
  universal-model.md 4.2 (vacuous Unresolved).
- Fix direction: reject any header except `lang` with
  `CompileError::Unsupported` until the polarity map exists, or route
  through `RuleProgram::interpret`. Add `subjects_examined` to
  `Outcome`.

**M3 (MEDIUM): the applicability resolver ignores capability cells for
parsed files.**
- Where: gob-check/src/applicability.rs:155-180.
- What's wrong: `needs` is consulted only when `facts.opaque`. For a
  parsed file, only parse failure and `min_fidelity` matter. A universal
  rule needing `TestItems` runs on CSS (cell NA), and one needing
  `Effects` runs on Rust (cell Gap, which should be Unresolved), so the
  rule's own code decides silently. Separately, `opaque_precision`
  (line 108-115) returns NotApplicable for every non-Comments need on an
  adapter-less file. A Go file therefore gets no DOC001 or COV001 and no
  Unresolved, contradicting testing.md 4 ("an artifact with no adapter
  yet is unresolved with reason fidelity"). This one is acknowledged
  in code under ~59MXB7Z.
- Fix direction: for parsed files, look up `gob_caps::precision(lang,
  cap)` for each need. NotApplicable gives NotApplicable, None gives
  Unresolved("capability gap: <cap>"). Land ~59MXB7Z.

**M4 (MEDIUM): matrix cells contradict the fidelity ladder.**
- Where: gob-caps/src/matrix.rs:46, 48.
- What's wrong: Python and TypeScript are F2 ("no apply edges") but
  declare `apply_targets = by-name (May)`, which is the F3 property.
  Fidelity and cells are both hand-written, so neither checks the
  other.
- Fix direction: derive fidelity from the cells (F3 iff `apply_targets`
  is provided, and so on) with a const assertion, then measure both by
  corpus (testing.md 5).

**L1 (LOW): `Precision` derives `Ord` across unrelated ladders.**
- Where: gob-caps/src/capability.rs:113-114.
- What's wrong: this gives `Manifest > Keyword > ... > Lexical`, which
  is meaningless. Any `>=` comparison of precisions is a latent bug.
- Fix direction: drop `PartialOrd`/`Ord`, or define per-capability
  chains.

**L2 (LOW): catalog language ids disagree with gob-caps `Lang`.**
- Where: gob-plan/src/catalog.rs.
- What's wrong: catalog ids are `"tsx"`, `"jsx"`, `"html"`, while the
  canonical `Lang::TypeScript.name()` is `"typescript"`.
  `Kind::answered_in("typescript")` is false for `element`.
- Fix direction: key the catalog on `gob_caps::Lang`.

**L3 (LOW): catalog fields the executor cannot read.**
- Where: gob-plan/src/exec.rs:355.
- What's wrong: catalog fields such as `attribute.tokens` pass
  `check_field` but `field_of` returns `Val::Unknown`, so a rule using
  them is permanently Unresolved.
- Fix direction: reject unreadable fields at compile time.

**L4 (LOW): "Must" from the purely lexical view in mutable-global
languages.** `ScopeGraph::from_term` marks every lexical edge Must.
For Python module scope, a later `helper = mock` rebinding, or a
`global` write from another function, makes the Must edge from
`helper()` to `def helper` wrong unless the Python fold lowers
assignments to binders and adds `may_define` hints. I did not verify
the Python fold's handling, so this is a conformance-test request, not
a confirmed bug.

## 3. Language-design review of GRL

1. **Ambiguity.** Two kinds:
   - The ~K0FVJFM shapes (leading `where` after an open binding;
     `reaches ... via a, b` inside `any { }`).
   - M1's connective continuation after a quantifier body.

   Two more grammar issues are not ambiguities but are underspecified:
   - `term ARITH term` has no precedence or associativity in section 5.
     The parser has additive and multiplicative levels (cond.rs:592-615),
     but the spec does not.
   - `in` is overloaded: membership `p in xs`, `in unit`, and ranges
     `a..b`. The parser decides `in unit` by looking ahead for "not
     followed by a dot" (cond.rs:396-398), so a variable named `unit`
     changes the parse.

   The spec's own examples do not parse against its grammar.
   `directive "todo"` (TODO001) is not a `shape`, since the grammar has
   KIND with optional `(field_eq...)` only. The parser accepts a string
   argument (parse/cond.rs:120-123), so the grammar text is stale.
   Regenerate the EBNF from the parser, or test the spec's code blocks
   against it as gob-mdtest does.
2. **Compositionality.** Mostly good: anonymous shapes desugar to
   `some`, defs are named predicates, and clause order is irrelevant.
   Two constructs are not compositional:
   - `report ... when` "first that holds, in text order" makes findings
     depend on clause order. With K3 it is unspecified what happens when
     an earlier `when` is Unknown and a later one is Yes. State it: an
     earlier Unknown makes the binding Unresolved, or fires the later
     one with an Unresolved note.
   - Witnesses: "first witness in source order" may be a May witness
     while the rule fires on a Must witness. Choose the first Yes
     witness.
3. **Static typing.** Names are checked against a catalog (the core
   principle) and side relations are typed from JSON schemas. That is
   the right design and matches QL's typed predicates (Avgustinov et al.
   2016). Missing:
   - a type of answers (which fields may be Unknown is in the catalog as
     `may_be_unknown` but unused by any checker);
   - capability types per word, so `lang [css]` plus the word `test` is
     a compile error rather than a runtime NA.

   With the catalog keyed on `Lang` and capability, "a word whose
   capability is NA or Gap in every language of `lang`" becomes GRL006
   or a new code, and the rule-authoring compile-time guarantee extends
   to GRL.
4. **Error messages.** The policy of using the user's words, not the
   theory's, plus golden tests, is good and consistent with the survey
   evidence. With the K3 semantics of 2.3, add one message class:
   "this `not` makes the rule Unresolved wherever `t calls f` is only
   possible", printed by `rule why`.
5. **How per-language patterns embed.** Snippets are quasi-quotation
   (Semgrep style, with `$X`, `$$$XS` and the language's own ellipsis).
   `as KIND` selects a node, and `as roles` lifts to U. This is the
   right split.
   - Comby (van Tonder and Le Goues 2019) shows the language-agnostic
     end of the design space.
   - tree-sitter queries and srcML show the typed-kind end.
   - The design risk is `as roles`. Lifting a Rust snippet to U roles
     and matching in Python means rho_Rust and rho_Python must agree on
     role attributes. That is a cross-adapter commuting condition
     (informally, a Galois-connection compatibility between per-language
     abstractions and U), and it should be a corpus test per role:
     the same logical shape in three languages lifts to one U pattern
     (testing.md 4 "parity cases" is the hook).
   - State the metavariable semantics: whether repeated `$X` is
     syntactic equality (Semgrep unification), alpha-equivalence, or
     digest equality. Alpha-equivalence via the canonical stream is the
     natural choice in U.
6. **One semantics for universal and per-language rules.** The intent is
   right: one evaluator, with `lang` deciding vocabulary and
   applicability. Today there are two models (U's scope graph and
   `SymbolGraph`), and the language-specific rules use the second. One
   semantics requires one relational structure. Recommendation R3.
7. **Prior art the spec should cite.**
   - Rascal (Klint, van der Storm and Vinju 2009): relational calculus
     plus patterns over parse trees, the closest single-tool analogue.
   - Spoofax and Statix (Kats and Visser 2010; van Antwerpen et al.
     2016, 2018): declarative name binding over scope graphs, which is
     what bind_L should be written in eventually.
   - Attribute grammars (Knuth 1968): the classical home for
     "per-language facts computed by structural recursion", which is
     what rho_L and bind_L are.

## 4. Recommendations, ranked (would-be ticket titles with scope)

1. **fix(gob-ir): an Unknown or unclassified edge widens hi to the
   frontier instead of being dropped.** Scope: eval/ctx.rs rel_calls and
   rel_resolves, eval/relation.rs (an `unknown_out` set and a closure
   rule), program.rs (keep strata poison). Tests: the two H1 scenarios.
   This is the only fix that changes verdicts today.
2. **docs(universal-model): restate Theorem 2 over lo/hi relation pairs
   with well-founded (two-pass) fixpoints.** Scope: sections 4.1-4.5.
   - Define Answer as an interval in the powerset lattice with the
     knowledge order.
   - State the adapter hypothesis R_lo <= R_true <= R_hi.
   - Replace "FO+LFP, equivalently stratified Datalog" with "stratified
     Datalog with aggregation; recursion only positive and only in
     catalog closures".
   - Prove soundness by induction on strata, using monotonicity in the
     information order, citing TVLA's embedding theorem as the model.
   - Prove exactness on the closed fragment from the two-pass fixpoint
     (which equals WFS there).
   - Restate Theorem 3(a) about L, not U. Fix the Theorem 1 wording.
3. **docs(grl-spec): a denotational semantics of GRL into K3 over lo/hi
   structures.** Scope: new section 7.0, roughly one page.
   - [[cond]] compositional.
   - Quantifiers over Bounds domains with the "may have hidden members"
     disjunct.
   - `count` as intervals with interval comparison.
   - `reaches within N` with truncation as Unknown (fixes the COV001
     honesty bug).
   - `certainly`/`possibly` restricted to positive positions.
   - Polarity as the Yes/Unknown/No map of 2.3, replacing "on Must
     facts".
   - NotApplicable removed from the value space and moved to static
     (rule, language) applicability.
   - Defs as materialised views.
   - Cost class as variable width.
4. **feat(gob-ir): one relational structure for rules; lower
   SymbolGraph's status edges into U relations.** Scope: gob-symbols
   adapters emit import and call resolution as scope-graph edges with
   status (or a `Relation` view with lo/hi). gob-ir exposes the catalog
   relations. Without this, R5 cannot be sound.
5. **feat(gob-plan): compile GRL AST to plan IR and run it through a K3
   executor with polarity and subject accounting; migrate TODO001,
   DOC002 and INV002 first.** These three are the cheapest: TODO001
   needs `comment` plus `directive` kinds, DOC002 needs `link`/`file`,
   INV002 needs `import` plus `config`. Then COV001 once R1 and R4 land.
   Acceptance: the hand-written and GRL versions agree on the existing
   corpora (differential test), then delete the Rust version.
6. **fix(gob-plan): resolve the quantifier-body ambiguities (extend
   ~K0FVJFM with the `and`/`or` continuation).** Scope: cond.rs binding,
   grl-spec section 5, printer generator.
7. **fix(gob-check): the applicability resolver reads the matrix for
   parsed files; GRL `needs` becomes capabilities and side relations
   move to `reads`.** Scope: applicability.rs:155-180,
   grl/parse/rule.rs:302, grl-spec sections 5 and 6, catalog keyed on
   `gob_caps::Lang`.
8. **test(gob-ir): property tests that try to falsify Theorems 2 and 3.**
   Scope: tests/soundness.rs with proptest.
   - Generate a random term plus a scope graph with Must, May and
     Unknown edges.
   - Generate random concretisations: for each May set choose a
     subset; for each Unknown choose any target, including outside the
     set.
   - Generate random formulas from a small grammar: atoms, not/and/or,
     some/no, count compared with k, bounded and unbounded reach.
   - Check that every Yes or No from the K3 evaluator equals the
     classical answer in EVERY sampled concretisation (soundness).
   - Check that on concretisation-free (closed) structures the K3
     answer is never Unknown and equals the classical one (exactness).
   - Shrinking gives minimal counterexamples. This would have found H1,
     the polarity-table bug and the `within` bug mechanically.
9. **test(gob-caps, gob-symbols): fidelity measured, not declared.**
   Derive the level from capability cells (const assert), and measure
   both with per-adapter corpora including an oracle column (as D119
   proposes). Fixes M4 and the testing.md 5 gap.
10. **Optional: a Lean 4 model of the honesty theorem.** Scope: about
    300 lines. K3 as a Lean inductive with the information order; a
    structure with lo/hi relations; formulas with stratified negation
    and positive closure; theorem `eval_sound : eval phi S = some b ->
    forall C, concretises C S -> holds C phi = b`. The proof is by
    induction on strata and is mechanical. TLA+ is the wrong tool here
    (there is no concurrency). The proptest of item 8 delivers most of
    the value at a tenth of the cost, so do it first.
11. **docs(universal-model): Belnap-style conflict as a reason, not a
    value.** Combine sources by knowledge-order join, collapse Both to
    Unknown with reason `conflict`, and list the sources. Applies to
    directives versus resolution, `SymbolGraph` versus U, and D119
    annotation versus inference.

## 5. Staged draft cohesion.md (D118, D119; coordinator request)

### 5.1 COH001 bounds: the ordering is correct; three definitions are missing

**Bound direction (correct).** Adding edges can only merge components.
With Must <= True <= Must + May on edge sets:

    k_may = #components(Must + May) <= k_true <= #components(Must) = k_must

So lo = k_may and hi = k_must is the right orientation. "Fire when
lo >= 2" is sound (at least two jobs in every completion), "clean when
hi <= 1" is sound, and Unresolved is right in between.

**This soundness holds only if three conditions hold:**

1. **May is complete (the closed-world hypothesis of 2.2.5 again).** An
   unknown callee, an opaque statement, or a statement in an opaque
   region must be connected by May to every statement that reads or
   writes non-local or aliased state. Simplest rule: it is adjacent to
   everything, which collapses lo to 1, so the result is Unresolved and
   never a false fire. If unknown effects are dropped the way `rel_calls`
   drops Unknown edges (H1), lo is overestimated and COH001 fires on a
   false premise.
2. **Control dependence must be an edge (soundness bug in the draft as
   written).** The draft builds def-use only ("an edge when one
   statement reads what another writes"). Slicing needs data AND
   control dependence (Weiser 1984; the program dependence graph of
   Ferrante, Ottenstein and Warren 1987). Counterexample:

       def f(xs, flag):
           ok = validate(flag)
           if ok:
               send(xs)

   If `send(xs)` is a statement node and `xs` is a parameter (glue),
   then `send(xs)` has no data edge to `ok = validate(flag)`. That gives
   two components, so lo = 2 and COH001 fires, but this is one job
   (validate then send). Fix: a statement is control-dependent on its
   guarding condition, and that is a Must edge, or the `if` is one node
   containing its body. Choose one and state the statement granularity.
3. **"Must" means a static dependence, not a certain execution.** A use
   reached by two definitions (on two branches) has two real static
   dependence edges. Both are Must for slicing purposes. May is reserved
   for aliasing, heap and unknown effects. The draft's wording
   ("provably refers to that write") invites marking branch-dependent
   reaching definitions as May, which would only lose precision.

**Glue.**

- **Parameters are glue only if read-only.** `def f(buf): buf.append(x);
  n = len(buf)` has a real dependence through `buf`. Treat a parameter
  as glue unless some statement writes it, or may write it through a
  method call or an alias, in which case its writes are ordinary
  def-use edges (May through calls).
- **"Joined by the return value is one pipeline" contradicts the cited
  measure.** Bieman and Ott's functional cohesion is defined over the
  slices of each OUTPUT (the returned values and outputs), with "glue"
  tokens in more than one slice and "superglue" tokens in all of them
  [unsourced at the definitional level: the paper's PDF was fetched
  (URL in section 7) but its text is not extractable; this is from
  memory of the paper; the metadata is fetched]. Under that measure,
  `return (a, b)` with independent `a` and `b` is two output slices with
  no glue, which is LOW cohesion. The draft's rule merges them through
  the return node, so it is one job.

  Pick one definition and cite accordingly:
  - (a) components of the dependence graph with the return node
    excluded and each returned component an output; this matches Bieman
    and Ott;
  - (b) the draft's coarser "independent computations" notion; then do
    not cite Bieman and Ott as the definition, cite them as related
    work.

**Trivial slices.** Define them as statements whose only effects are in
a configured vocabulary (log, metric, assert). Remove the statements
before computing components, and add no edges through them.

- Removing a bridging trivial statement can SPLIT a component (`x = a();
  log(x, y); y = b()`). That is intended ("logging does not glue jobs"),
  but say so.
- A slice with no output (no returned value, no non-trivial effect) is
  dead code, not a job. Exclude it, so COH001 does not double-report
  dead stores (leave those to a dead-code rule).
- Add a minimum slice size knob, so a 3-line function with two
  independent assignments is not Warn.

### 5.2 Citations for D118 and D119 (all fetched; URLs in section 7)

| [cite] in the draft | Source |
|---|---|
| Bieman and Ott 1994 | J. M. Bieman, L. M. Ott, "Measuring functional cohesion", IEEE TSE 20(8), 1994, doi:10.1109/32.310673; author PDF http://www.cs.colostate.edu/~bieman/Pubs/tse94.pdf (fetched; text not extractable) |
| Ott and Thuss | L. M. Ott, J. J. Thuss, "Slice based metrics for estimating cohesion", IEEE METRICS 1993, doi:10.1109/metric.1993.263799; earlier "The relationship between slices and module cohesion", ICSE 1989, doi:10.1109/icse.1989.714420; also Ott and Bieman, "Program slices as an abstraction for cohesion measurement", IST 1998, doi:10.1016/s0950-5849(98)00092-5 |
| Beck, Composed Method / SLAP | Not fetchable: the book (K. Beck, Smalltalk Best Practice Patterns, Prentice Hall 1997) has no open page I could retrieve (O'Reilly returned 403). Fowler's "Function Length" (https://martinfowler.com/bliki/FunctionLength.html, fetched) credits Beck's Smalltalk examples for the small-method style, but does not name Composed Method. Mark "Composed Method" and "SLAP" [unsourced]. |
| Marcus and Poshyvanyk | A. Marcus, D. Poshyvanyk, "The conceptual cohesion of classes", ICSM 2005, doi:10.1109/icsm.2005.89. Note this is CLASS cohesion over LSI of identifiers and comments; applying it to functions is an extension, so say so. |
| Tsantalis and Chatzigeorgiou 2011 | N. Tsantalis, A. Chatzigeorgiou, "Identification of extract method refactoring opportunities for the decomposition of methods", JSS 84(10), 2011, doi:10.1016/j.jss.2011.05.016 (CSMR 2009 version doi:10.1109/csmr.2009.23) |
| Slicing and dependence (needed by 5.1) | Weiser 1984 doi:10.1109/tse.1984.5010248; Ferrante, Ottenstein, Warren 1987 doi:10.1145/24039.24041; Horwitz, Reps, Binkley 1988 doi:10.1145/53990.53994 |
| Gradual typing | Siek and Taha, "Gradual typing for functional languages", Scheme Workshop 2006, http://scheme2006.cs.uchicago.edu/13-siek.pdf (fetched; defines type consistency). Tobin-Hochstadt and Felleisen, "Interlanguage migration: from scripts to programs", OOPSLA companion 2006, doi:10.1145/1176617.1176755; "The design and implementation of Typed Scheme", POPL 2008, doi:10.1145/1328438.1328486. Wadler and Findler, "Well-typed programs can't be blamed", ESOP 2009, doi:10.1007/978-3-642-00590-9_1 |
| Soundness of TS and Python checkers | Takikawa et al., "Is sound gradual typing dead?", POPL 2016, doi:10.1145/2837614.2837630 (the cost of sound boundaries). Bierman, Abadi, Torgersen, "Understanding TypeScript", ECOOP 2014, doi:10.1007/978-3-662-44202-9_11. TypeScript handbook, "Type Compatibility" (https://www.typescriptlang.org/docs/handbook/type-compatibility.html, fetched): "The places where TypeScript allows unsound behavior were carefully considered" (parameter bivariance, optional and rest parameters). Vitousek et al., "Design and evaluation of gradual typing for Python", DLS 2014, doi:10.1145/2661088.2661101 |
| mypy, pyright, ty on Any and strict | mypy "Dynamically typed code" (https://mypy.readthedocs.io/en/stable/dynamic_typing.html): Any is assignable to and from every type. mypy `--strict` (https://mypy.readthedocs.io/en/stable/command_line.html): "strict will catch type errors as long as intentional methods like type ignore or casting were not used". pyright `strict` config (https://raw.githubusercontent.com/microsoft/pyright/main/docs/configuration.md). ty FAQ (https://docs.astral.sh/ty/reference/typing-faq/): "Unknown ... behaves the same way as Any, but appears implicitly", and "ty doesn't currently have a flag called --strict". |

Consequence for D119 section 2.2: `[types] trust = "checked"` names
"strict mode" for ty, but ty has no `--strict` flag (fetched FAQ). The
setting must name ty's actual rule configuration, or drop ty from the
strict list.

### 5.3 The precision lattice exact / claimed / inferred / dynamic

1. **It mixes provenance with trust.** "claimed" with
   `trust = "annotated"` becomes "exact". "inferred" (adapter-local
   flow) is stronger than "claimed" but weaker than "exact". Make two
   coordinates:
   - provenance in {checker, annotation, local-inference, none}, a set
     and not an order;
   - the derived status in {Must, May, Unknown}, the existing chain,
     computed by a policy function from (provenance, trust setting,
     closure conditions).

   Status composes by meet along a chain. Provenance composes by union,
   which is what `rule why` prints.
2. **"claimed: treated as May" is unsound (HIGH for D119).** May sets
   must contain the true referents (universal-model.md 4.4). An
   unverified annotation `def run(h: Handler)` gives the May set
   {implementors of Handler}. If a caller passes a non-Handler (legal at
   runtime; mypy lets Any flow anywhere, fetched), the true target is
   outside the set. P- rules (COV001 counting a May-reached test as
   "only May", so not a fire) are fine. But P+ "certify clean when the
   offender is not in hi" and Pc "no path inside hi" become wrong. An
   unverified claim may narrow only ordering and explanations, never hi.
   So the claim must be Unknown with a ranked candidate hint, or May
   only under explicit `trust = "annotated"` with the report saying so.
3. **"exact" from a clean checker run on one file is not exact.** Sound
   gradual typing needs runtime checks at the typed and untyped boundary
   (Siek and Taha 2006; Tobin-Hochstadt and Felleisen 2006, 2008;
   Wadler and Findler 2009). TypeScript and mypy erase types, which is
   exactly what Takikawa et al. 2016 measure the cost of avoiding. A
   strict-clean file can still receive a wrong value from an unchecked
   caller, through Any, `cast`, `# type: ignore`, or an untyped
   dependency. The condition for "exact" therefore has to be
   whole-program: every module that can reach the site through the
   import graph is checked strict with no Any flowing in. Otherwise the
   result is "claimed". The draft's "ignore comments demote their line"
   is necessary but not sufficient, because the damage is at the
   callee, not the line.
4. **"inferred: Must within the flow fact's scope" needs a no-patching
   side condition** for Python and JS dispatch. `x = Foo(); x.m()` is
   Must to `Foo.m` only if no `setattr(Foo, "m", ...)` or prototype
   assignment exists in the program. Otherwise it is May. The adapter
   can check this syntactically: scan for writes to class attributes or
   prototypes. With an opaque `eval`, the answer is Unknown.
5. **Composition along a dispatch chain.** For a chain of resolutions
   s1 -> s2 -> ... -> sn, where each hop's target depends on a type
   fact at that site, the status of the composite is the meet of the
   hop statuses (Must > May > Unknown). That is `Status::meet`
   (scope.rs:35), and it is a bounded chain, hence a lattice, and meet
   is monotone. Provenance is the union of hop provenances. Two caveats:
   - A May hop multiplies candidates. The composite May set is the
     union over the hop's candidates of the downstream sets, which is
     relational composition. That is already `Relation::compose` with
     min along and max across.
   - An Unknown hop must widen to top downstream (H1), not end the
     chain.
6. **Conflicting sources (5.3 item 1 and 2.7).** When an annotation says
   Foo and local inference says Bar, take the knowledge join. That is
   Both, collapsed to Unknown with reason `conflict:annotation-vs-inference`,
   which is a likely bug in the user's code worth surfacing. It is the
   one place in this design where Belnap's fourth value earns its keep.
7. **D121 effects claims are inconsistent with D119.** Section 5 says
   one unverified `grimble:effects none` claim "turns the callers'
   answers precise", while D119 says unverified claims are May. Under
   Theorem 3, a caller's answer derived from an UNVERIFIED claim must
   carry the claim as a premise. Either the verdict is Unresolved with
   reason `assumed:<claim>`, or it is reported as "conditional on the
   claim at X" (assume-guarantee without the guarantee is just an
   assumption). Otherwise a false claim produces a definite clean on
   every caller.

## 6. Notes: checked and found correct, and boundaries of this review

Checked and correct:

- K3 connectives (answer.rs).
- The two-pass closure as a sound and exact fixpoint for positive
  recursion (relation.rs:114-140).
- Alpha-invariance machinery and its property tests (properties.rs).
- Valence-aware binder scoping (`binds_over`, scope.rs walk) and
  `free_vars`.
- The `RuleProgram::interpret` polarity table for set, pair, count and
  reach observations, which matches universal-model.md 4.2 when the
  check builds Bounds correctly (program.rs:403-500).
- Subject accounting (vacuous, must_measure, whole-scope NA) in
  `finish`.
- Exec's spread handling for `has attribute`, which is Unknown when only
  a spread could supply the attribute.
- The plan validator's tree and ordering invariants (validate.rs
  header).

COH001's bound direction is correct, as stated in 5.1.

Skimmed or skipped:

- gob-symbols adapters' internal resolution (`SymbolGraph`, about
  3k lines in graph.rs) was not audited for May-completeness. H1-style
  drops may exist there too, and that is where production COV001 gets
  its edges.
- grimble-bind owner selection (select.rs) and const_value (866 lines)
  were read only at the API level.
- The research notes were read by heading plus the sections cited.
  calculi.md's 11 `[verify]` tags were not individually resolved, but
  the citations they gate (Rice, Wells, Immerman, Vardi) are now fetched
  in section 7.
- The plan codec was not reviewed.
- No tests were run (read-only brief; the disk and builder limits in
  the memory notes apply).

## 7. Sources (fetched 2026-10-08)

Bibliographic metadata was fetched from the Crossref REST API
(api.crossref.org) unless a direct URL is given. The URL listed is the
DOI resolver.

U, terms, binding:

- Harper, Practical Foundations for Programming Languages, 2nd ed.,
  CUP 2016, https://doi.org/10.1017/cbo9781316576892 (metadata only;
  the claim "ABTs are chapter 1" is [unsourced]).
- Allais, Atkey, Chapman, McBride, McKinna, "A type and scope safe
  universe of syntaxes with binding", ICFP 2018,
  https://doi.org/10.1145/3236785 (JFP 2021:
  https://doi.org/10.1017/s0956796820000076). Note: the spec cites
  "Allais et al. 2018", which is correct; the brief's "Allais, McBride,
  Boutillier" author list is not.
- Goguen, Thatcher, Wagner, Wright, "Initial algebra semantics and
  continuous algebras", JACM 1977, https://doi.org/10.1145/321992.321997
- Knuth, "Semantics of context-free languages", Math. Systems Theory
  1968, https://doi.org/10.1007/bf01692511

Scope graphs and Statix:

- Neron, Tolmach, Visser, Wachsmuth, "A theory of name resolution",
  ESOP 2015, https://doi.org/10.1007/978-3-662-46669-8_9
- van Antwerpen, Neron, Tolmach, Visser, Wachsmuth, "A constraint
  language for static semantic analysis based on scope graphs", PEPM
  2016, https://doi.org/10.1145/2847538.2847543
- van Antwerpen, Bach Poulsen, Rouvoet, Visser, "Scopes as types",
  OOPSLA 2018, https://doi.org/10.1145/3276484
- Rouvoet et al., "Knowing when to ask", OOPSLA 2020,
  https://doi.org/10.1145/3428248
- Statix docs, https://spoofax.dev/references/statix/
- Kats, Visser, "The Spoofax language workbench", OOPSLA 2010,
  https://doi.org/10.1145/1869459.1869497
- NaBL and SDF3 primary papers: [unsourced].

Truth values and lattices:

- Stanford Encyclopedia of Philosophy, "Many-valued logic",
  https://plato.stanford.edu/entries/logic-manyvalued/ (strong Kleene
  K3; weak Kleene, Bochvar B3 "logic of nonsense"; Kleene 1938 for
  partiality).
- Belnap, "A useful four-valued logic", 1977,
  https://doi.org/10.1007/978-94-010-1161-7_2
- Ginsberg, "Multivalued logics", Comput. Intell. 1988,
  https://doi.org/10.1111/j.1467-8640.1988.tb00280.x
- Fitting, "Bilattices and the semantics of logic programming", JLP
  1991, https://doi.org/10.1016/0743-1066(91)90014-g
- Fitting, "A Kripke-Kleene semantics for logic programs", JLP 1985,
  https://doi.org/10.1016/s0743-1066(85)80005-4

Abstract interpretation and three-valued analysis:

- Cousot, Cousot, "Abstract interpretation", POPL 1977,
  https://doi.org/10.1145/512950.512973
- Cousot, Cousot, "Systematic design of program analysis frameworks"
  (Galois connections), POPL 1979, https://doi.org/10.1145/567752.567778
- Sagiv, Reps, Wilhelm, "Parametric shape analysis via 3-valued logic",
  TOPLAS 2002, https://doi.org/10.1145/514188.514190
- Bruns, Godefroid, "Model checking partial state spaces with 3-valued
  temporal logics", CAV 1999, https://doi.org/10.1007/3-540-48683-6_25

Datalog semantics and complexity:

- Apt, Blair, Walker, "Towards a theory of declarative knowledge", 1988,
  https://doi.org/10.1016/b978-0-934613-40-8.50006-3
- Van Gelder, Ross, Schlipf, "The well-founded semantics for general
  logic programs", JACM 1991, https://doi.org/10.1145/116825.116838
- Przymusinski, "Well-founded semantics coincides with three-valued
  stable semantics", Fund. Inf. 1990, https://doi.org/10.3233/fi-1990-13404
- Kolaitis, "The expressive power of stratified logic programs",
  Inf. Comput. 1991, https://doi.org/10.1016/0890-5401(91)90059-b
- Immerman, "Relational queries computable in polynomial time",
  Inf. Control 1986, https://doi.org/10.1016/s0019-9958(86)80029-8
- Vardi, "The complexity of relational query languages", STOC 1982,
  https://doi.org/10.1145/800070.802186
- Immerman, "Languages that capture complexity classes", SIAM J. Comput.
  1987, https://doi.org/10.1137/0216051
- Barrington, Immerman, Straubing, "On uniformity within NC1", JCSS 1990,
  https://doi.org/10.1016/0022-0000(90)90022-d
- Libkin, "Expressive power of SQL", TCS 2003,
  https://doi.org/10.1016/s0304-3975(02)00736-3
- Libkin, Elements of Finite Model Theory, 2004,
  https://doi.org/10.1007/978-3-662-07003-1
- Bancilhon, "Naive evaluation of recursively defined relations", 1986,
  https://doi.org/10.1007/978-1-4612-4980-1_17 (attribution of
  semi-naive evaluation to this paper is [unsourced]).
- Ross, Sagiv, "Monotonic aggregation in deductive databases", PODS 1992,
  https://doi.org/10.1145/137097.137852
- Green, Karvounarakis, Tannen, "Provenance semirings", PODS 2007,
  https://doi.org/10.1145/1265530.1265535
- Atserias, Grohe, Marx, "Size bounds and query plans for relational
  joins", FOCS 2008, https://doi.org/10.1109/focs.2008.43
- Beeri, Fagin, Maier, Yannakakis, "On the desirability of acyclic
  database schemes", JACM 1983, https://doi.org/10.1145/2402.322389
- Gottlob, Koch, "Monadic datalog and the expressive power of languages
  for web information extraction", JACM 2004,
  https://doi.org/10.1145/962446.962450

Trees and patterns:

- Thatcher, Wright, "Generalized finite automata theory ...", 1968,
  https://doi.org/10.1007/bf01691346
- Doner, "Tree acceptors and some of their applications", JCSS 1970,
  https://doi.org/10.1016/s0022-0000(70)80041-1
- Angluin, "Finding patterns common to a set of strings", JCSS 1980,
  https://doi.org/10.1016/0022-0000(80)90041-0
- Ehrenfeucht, Rozenberg, "Finding a homomorphism between two words is
  NP-complete", IPL 1979, https://doi.org/10.1016/0020-0190(79)90135-2

Rule and query languages:

- Avgustinov, de Moor, Peyton Jones, Schafer, "QL: Object-oriented
  queries on relational data", ECOOP 2016,
  https://drops.dagstuhl.de/storage/00lipics/lipics-vol056-ecoop2016/LIPIcs.ECOOP.2016.2/LIPIcs.ECOOP.2016.2.pdf
  (fetched: "QL compiles to Datalog"; stratified recursion).
- CodeQL docs, "Recursion",
  https://codeql.github.com/docs/ql-language-reference/recursion/
  ("recursion is only allowed under an even number of negations").
- Jordan, Scholz, Subotic, "Souffle: on synthesis of program analyzers",
  CAV 2016, https://doi.org/10.1007/978-3-319-41540-6_23; Souffle docs,
  https://souffle-lang.github.io/aggregates
- Semgrep pattern syntax, https://semgrep.dev/docs/writing-rules/pattern-syntax
  (ellipsis, metavariable unification).
- Comby, https://comby.dev/docs/basic-usage; van Tonder, Le Goues,
  "Lightweight multi-language syntax transformation with parser parser
  combinators", PLDI 2019, https://doi.org/10.1145/3314221.3314589
  (Crossref metadata).
- tree-sitter queries,
  https://tree-sitter.github.io/tree-sitter/using-parsers/queries/1-syntax.html
- Collard, Decker, Maletic, "srcML", ICSM 2013,
  https://doi.org/10.1109/icsm.2013.85
- Klint, van der Storm, Vinju, "RASCAL", SCAM 2009,
  https://doi.org/10.1109/scam.2009.28

Undecidability:

- Rice, "Classes of recursively enumerable sets and their decision
  problems", Trans. AMS 1953,
  https://doi.org/10.1090/s0002-9947-1953-0053041-6
- Wells, "Typability and type checking in System F are equivalent and
  undecidable", APAL 1999, https://doi.org/10.1016/s0168-0072(98)00047-5

Cohesion, slicing, gradual typing: see the table in 5.2 (each row lists
its DOI or URL).

Unsourced in this report:

- Beck, Composed Method and SLAP;
- NaBL and SDF3 primary papers;
- DRed (Gupta, Mumick and Subrahmanian 1993);
- tree automata with equality constraints;
- approximation fixpoint theory as the general form of the lo/hi
  construction (Denecker, Marek and Truszczynski);
- the definitional details of Bieman-Ott glue and superglue (PDF
  fetched, text not extractable);
- semi-naive evaluation's attribution to Bancilhon 1986.
