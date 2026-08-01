# Clone-detection state of the art vs. frob.dup -- T-0187 phase 1 survey

Status: exhaustive against the enumerated universe below (26 items,
0 pending, 0 blocked -- see "Coverage proof").

## 0. What frob.dup actually does today (read from source, not the design docs alone)

Rungs R1-R7 are designed in `docs/modules/dup.md`; implementation lives in
`src/frob/dup/{_core,_pipeline,_rules,_cache,_legacy*}.py` and the Rust
kernels in `frob-core/src/lib.rs`. Ground truth as of this pass, which
corrects two things the ticket's "known debt" summary gets stale on:

- **R4 verification is REAL Zhang-Shasha APTED now, not Levenshtein.**
  `frob-core/src/lib.rs::apted_similarity` (line 355) implements true
  postorder Zhang-Shasha tree edit distance over parent-index arrays
  (`build_postorder`, `keyroots`, `zhang_shasha_distance`). It is wired in
  `_pipeline/_callgraph.py::_apted_similarity_for_pair` via
  `frob.lang.symbol_tree` + `frob.lang._common.flatten_tree` for real
  subtree structure -- this is the *primary* R4 verification path.
  `frob_core::tree_edit_similarity` (statement-sequence Levenshtein, line
  143) still exists and is used only as the **fallback** when
  `frob.lang.symbol_tree` cannot be built for a candidate (`_pipeline.py`
  line ~44, `_split_statements`/`_statement_hashes` path, line 761-763).
  So: the ticket's premise ("statement-level Levenshtein instead of full
  APTED") is now half-stale -- APTED is implemented and wired as primary;
  Levenshtein survives only as the degraded fallback, which is a
  reasonable two-tier design, not undone debt.
- **R5 dataflow graph has a real primary path too.** `_build_dataflow_graph`
  (co-occurrence proxy: connects every identifier token within a
  heuristic statement chunk, labels by "immediately followed by `=`") is
  now the **fallback**; `_core_symbol_tree` + real `frob.lang` structure
  feeds a genuine def-use walk when available (`_pipeline.py` line ~60,
  617-621). The proxy remains the honest fallback for symbols
  `frob.lang.symbol_tree` cannot parse -- documented as such, not silently
  passed off as a real CFG/DFG in that branch.
- **R6 (`probe_equivalence`) is implemented and real** for Python-only,
  heuristically-pure pairs (token-blocklist purity check, `frob.fuzz`
  Arbitrary generators for scalar params, output comparison under a time
  budget). It is **not called from `find_clones`/the DUP gate path**, and
  no `frob dup --probe` CLI flag exists to reach it -- confirmed absent
  (no `probe`/`--probe` string anywhere under `src/frob/cli*`). This is
  the one debt item from the ticket brief that is still fully live:
  **R6 is implemented but functionally unreachable from the CLI.**
  T-0041 in `tickets-archive.md` is the historical record of this being
  spun off, not closed.
- **R7 (bounded SMT)** exists (`probe_smt_equivalence`, opt-in `z3-solver`)
  for tiny straight-line int/bool functions, refusing (`Err`) outside its
  accepted node set -- no silent approximation.
- **DUP001/DUP002 are wired into `frob.gates.__init__`** as `dup_gate`
  (T-0191), which runs the real `find_clones` pipeline and is registered
  as the opt-in `"clones"` gate. It stays off by default -- `[dup].enforce
  = true` in `frob.toml` turns it on -- and is silent (skipped, logged at
  debug) until a repo opts in, or if frob-core is not installed. When
  enforce is off (the default), `frob check`'s dup stage still runs only
  the legacy Type-1/2 scanner (`frob.dup._legacy` / `find_duplicates`);
  once enforce is on, DUP001/DUP002 also fire.

  <!-- frob:invariant INV-011 -->
- Caching is content-addressed (digest-keyed) with LRU eviction on
  pairwise verdicts (`.frob/dup.db`, `frob.dup._cache`); a real, working
  incrementality layer any new rung must plug into rather than duplicate.
- No pure-Python fallback policy for R3+ (`CoreUnavailable` if
  `frob_core` missing) is enforced literally and is a good precedent for
  every new kernel below: put it in Rust or don't ship it.

## 1. Enumerated universe (denominator = 26)

Token/lexical: 1 SourcererCC bag-of-tokens, 2 NiCad normalization.
Tree: 3 APTED exact TED, 4 DECKARD characteristic vectors, 5 generic AST
fingerprinting (beyond frob's current R3 canonical hash).
Metrics/hybrid: 6 Oreo (type-3/4 via metrics+embeddings).
Graph/semantic: 7 PDG-based (Krinke), 8 general CFG/DFG semantic clone
detection (beyond frob's WL-hash rung).
Learning-based: 9 CCLearner, 10 ASTNN, 11 FA-AST (GNN), 12 CodeBERT-style
embedding clone search -- each with a zero-model-weights feasibility
verdict.
Cross-language: 13 cross-language clone detection generally.
Scalability: 14 winnowing/MOSS (already adopted, dispositioned for
completeness), 15 MinHash/LSH (already adopted via `candidate_pairs`,
dispositioned), 16 suffix automata / generalized suffix trees.
Abstraction/reverse-templating: 17 anti-unification (Plotkin lgg), 18
higher-order anti-unification, 19 parameterized clone reporting
(template + bindings), 20 extract-function suggestion synthesis.
Meta/testing: 21 exhaustiveness-matrix design for detectors (frob-specific,
in the mold of T-0158).
Process items required by the brief: 22 ranked upgrade shortlist, 23
reverse-templating design sketch, 24 meta-test design, 25 proposed ticket
tree, 26 gate-integration status noted in section 0 (DUP001/002 wired as
the opt-in `dup_gate`, off by default via `[dup].enforce`) -- carried as
its own disposition since default-off enforcement means most ADOPT
verdicts still lack teeth in a repo that has not opted in.

## 2. Per-technique disposition

### 1. SourcererCC (bag-of-tokens, block-level, index-based)
Detects: Type-1/2, partial Type-3 (near-miss via token subset overlap).
Cost: O(n) tokenization, index lookup near O(1) amortized per block via
inverted index on token subsets; scales to hundreds of MLOC in the paper
(Sajnani et al., ICSE 2016).
Implementability: trivial in Python, no model. frob's R1/R2 (exact +
alpha-renamed token hash) already subsume SourcererCC's Type-1/2 case;
its distinguishing feature -- partial/overlap block index for Type-3 --
is arguably better replaced by R4's winnow+LSH which is finer-grained.
**Verdict: REJECT (superseded).** R1/R2/R4 already cover what SourcererCC
buys; adding its specific block-index structure duplicates R4 for no new
class of clone caught.

### 2. NiCad (normalization + textual/tree pretty-printing before diff)
Detects: Type-1/2/near-Type-3 via aggressive pretty-print normalization
(blank/comment stripping, identifier blinding, formatting canonicalization)
then a line-based diff with a similarity threshold.
Cost: linear per pair after normalization; comparisons still pairwise
within blocks.
Implementability: the *normalization* half (blind identifiers, strip
formatting-only differences) is exactly what frob's R2/R3 alpha-renaming
and canonicalization already do at the token/AST level, arguably more
principled than NiCad's pretty-print-and-diff approach.
**Verdict: REJECT (superseded), but ADOPT one narrow idea:** NiCad's
"potential clone filtering" pre-pass (cheap size/shape filters before
expensive comparison) is worth lifting into frob's candidate-pairs stage
as an additional cheap filter (min_tokens already does this; consider
also filtering by statement-count ratio before APTED). Sketch: a
size-ratio gate in `_pipeline.py` before `_apted_similarity_for_pair` is
called, cutting APTED invocations on wildly mismatched-length candidates.
Low effort, folds into existing R4 stage, not a new rung.

### 3. APTED (Pawlik & Augsten, exact tree edit distance, VLDB 2015/2016)
Detects: Type-3, some Type-4 dressing (restructured-but-similar trees) --
this is the algorithm frob names explicitly in its rung table.
Cost: APTED is O(n^3) worst case, O(n^2 log n) typical for real trees
(better than the earlier RTED bound in the common case); prohibitive
pairwise across a whole repo without candidate pruning first.
Implementability: **already implemented** -- `frob-core::apted_similarity`
is genuine Zhang-Shasha postorder DP (this repo's variant is Zhang-Shasha,
1989, not the newer APTED algorithm specifically, but solves the same
problem exactly; APTED's contribution over Zhang-Shasha is asymptotic
improvement on the search-space bound for the general RNA-tree case, not
correctness). For frob's tree sizes (single function bodies, generally
<200 nodes) Zhang-Shasha's cost is not the bottleneck -- LSH/winnow
pre-filtering already restricts pairs before TED runs.
**Verdict: ADOPT is already done.** One real gap: the doc calls it
"APTED" but the kernel is Zhang-Shasha -- naming nit only, not a
functional gap given tree sizes involved. No action needed unless
candidate volume grows to where the true APTED search-space pruning
would matter (defer, doesn't justify a ticket now).

### 4. DECKARD (Jiang et al., ICSE 2007 -- characteristic vectors + LSH)
Detects: Type-1/2/3 via numeric vectors summarizing AST subtree shape
(node-type counts per subtree), clustered via LSH/Euclidean neighbor
search instead of pairwise tree comparison.
Cost: vector construction O(n) per tree, then approximate nearest-neighbor
search sublinear per query -- this is DECKARD's whole point: avoid
pairwise TED at scale.
Implementability: straightforward in Rust -- a subtree characteristic
vector is a histogram over `frob.lang` node-type labels, no model weights.
frob's `candidate_pairs` (LSH on winnowed token fingerprints, R4) already
plays DECKARD's role at the *token* level; DECKARD's vectors operate at
the *tree-shape* level and would catch clones R4's token-winnowing misses
(e.g., same structural shape, heavily different tokens/identifiers beyond
alpha-renaming -- rare but real, e.g. two loops with the same nesting
shape doing different operations named differently that R3 canonicalization
undernormalizes).
**Verdict: ADAPT.** Add a DECKARD-style structural characteristic vector
as a cheap R3.5 pre-filter: per-subtree histogram of canonicalized node
labels (already available post-R3 canonicalization), bucketed via
Euclidean LSH (a second, cheap LSH stage next to the existing
fingerprint-based `candidate_pairs`) to catch structurally-similar-but-
token-different candidates before they'd ever collide in R4's
token-winnow buckets. Effort: medium (new Rust kernel + Python wiring),
strictly additive to candidate generation, does not replace anything.

### 5. Generic AST fingerprinting (beyond frob's own R3)
Detects: Type-1/2, structural Type-3 depending on fingerprint granularity.
Cost: linear.
**Verdict: REJECT (superseded)** -- R3's canonical hash (alpha-rename +
literal abstraction + commutative-operand ordering + control-flow
normalization) is already a stronger fingerprint than generic
literature baselines (most only alpha-rename); no external technique adds
a new capability class here.

### 6. Oreo (Saini et al., ICSE 2018 -- metrics + shallow NN for Type-3/4)
Detects: claims Type-3 and some Type-4 via software metrics (McCabe,
Halstead-style counts) fed to a lightweight fully-connected classifier
plus a token-based filter stage.
Cost: metric extraction linear; classifier inference is cheap once
trained, but **training requires labeled clone pairs** (BigCloneBench).
Implementability: the metric-extraction half is free (no model needed) --
computable from `frob.lang` symbol data (cyclomatic complexity, token/line
counts, nesting depth) with zero network/weights. The classification half
needs a trained model, which frob's "no model weights, no network calls"
constraint rules out for a CI-gating tool (no retraining story, no
labeled corpus in-repo, opaque threshold instead of the auditable
similarity-percent frob currently reports).
**Verdict: PARTIAL ADOPT / REJECT the model.** Adopt the metric-vector
idea as one more cheap candidate-pair filter (like DECKARD's vectors,
item 4) -- e.g. two symbols whose cyclomatic complexity and line count
differ by >2x are unlikely Type-3/4 partners, skip expensive TED. Reject
the learned classifier outright: it needs labeled training data and
opaque inference, which breaks frob's "gate output must be auditable
without a model" design rule (see item 12 below for the fuller argument).

### 7. PDG-based clone detection (Krinke 2001, program dependence graphs)
Detects: Type-4 (semantically equivalent, structurally different) by
isomorphic-subgraph matching over full program dependence graphs
(control + data dependence edges).
Cost: subgraph isomorphism is NP-hard in general; practical tools bound
it with heuristics (fixed-size sliding windows over the PDG, as in
Krinke's original work) -- still expensive at scale (quadratic-ish over
candidate PDG fragments even with bounding).
Implementability: frob's R5 (WL-hash over a def-use/control-flow
adjacency) is a cheaper *approximation* of exactly this idea -- WL graph
kernels are the standard scalable proxy for "does this program dependence
graph look like that one" without solving subgraph isomorphism exactly.
**Verdict: R5 is the correct-cost ADOPT of this family already; REJECT
doing full PDG subgraph isomorphism** -- it would be strictly more
precise but asymptotically worse, and WL-hash already buys most of the
same signal (reordered-but-dataflow-identical code) at graph-kernel cost.
One real gap: R5's CFG/DFG is honestly a co-occurrence proxy on the
fallback path (see section 0) -- closing that (real control-flow edges,
not just "same statement chunk") is the legitimate high-value follow-up,
not switching techniques.

### 8. General CFG/DFG-based semantic clone detection (beyond Krinke)
Same disposition as item 7 -- WL-hash (R5) is the scalable proxy already
chosen; the gap is fidelity of the graph construction (real CFG/DFG vs.
proxy), tracked as a follow-up to close, not a new technique to adopt.
**Verdict: ADAPT (close the existing gap, not a new rung).**

### 9. CCLearner (Li et al., ICSE 2017 -- token-feature + NN classifier)
Detects: Type-1/2/3/4 claimed, via hand-crafted token-frequency features
(counts of keywords/operators/literals per method) fed to a small
feed-forward network trained on labeled clone pairs (BigCloneBench).
Cost: feature extraction linear; classifier cheap at inference,
**training requires the labeled corpus**.
Implementability: same wall as Oreo -- needs a trained model + labeled
data frob does not ship or retrain.
**Verdict: REJECT.** No new capability over R1-R5 that doesn't require
training data; the token-frequency features it uses are strictly weaker
than R3's structural canonicalization.

### 10. ASTNN (Zhang et al., ICSE 2019 -- tree-structured RNN over AST
statement sequences)
Detects: Type-4 (claims strong results on OJClone/BigCloneBench),
by learning statement-level embeddings composed bottom-up over the AST
then fed to a bi-GRU + similarity classifier.
Cost: training is expensive (GPU); inference is a forward pass per
function, cheap once trained.
Implementability: requires trained RNN weights, a labeled training
corpus, and (for good results) a large enough code corpus to train
embeddings on -- all excluded by the "no model weights, no network"
constraint. Even if weights were vendored, no retraining/monitoring
story for drift as `frob.lang`'s node vocabulary evolves.
**Verdict: REJECT (needs training data/weights).** Documented honestly:
this is the strongest Type-4 result in the survey and frob is
deliberately walking away from it for architectural reasons (auditability
+ zero-dependency), not because it doesn't work.

### 11. FA-AST / GNN-based clone detection (Wang et al. 2020, flow-
augmented AST + GNN)
Detects: Type-4, augments the AST with control-flow/data-flow edges then
runs a graph neural network (GMN-style) for pairwise similarity.
Cost: training expensive (GPU, labeled data); inference is a GNN forward
pass per candidate pair.
Implementability: same wall as ASTNN -- trained weights + labeled corpus.
Notably its core insight (augment AST with flow edges before comparing)
IS something frob can steal *without* the GNN: that's precisely what a
real CFG/DFG-backed R5 (closing the item-7/8 gap) already aims at, using
WL-hash instead of a learned GNN as the read-out function. WL-hash and
GNN message-passing are mathematically related (GNNs are a
continuous relaxation of the WL test); frob is already on the
"free lunch" end of that spectrum.
**Verdict: REJECT the GNN; ADOPT the underlying idea already via R5's
graph-kernel proxy** (cross-reference item 7/8's ADAPT).

### 12. CodeBERT-style embedding clone search (general "encode function,
nearest-neighbor in embedding space")
Detects: broad Type-3/4 recall in published benchmarks, but requires a
pretrained language model (network fetch or vendored weights), an
embedding index (FAISS or similar), and produces distances with no
line-level alignment or human-auditable "why" -- the tool would report
"0.91 similar" with no statement correspondence, unlike R3/R4/R5's
explicit alignment output.
Cost: one forward pass per function at index time (needs a model);
nearest-neighbor query sublinear via ANN index.
Implementability: directly excluded by the ticket's zero-model-dependency
constraint, and independently a poor fit for a CI gate that must explain
*why* a violation fired (frob's DUP001 message names both regions +
alignment; embedding similarity alone cannot produce that).
**Verdict: REJECT, unconditionally, for this tool's design goals** --
not merely "no weights available" but "even with weights, the output
shape (opaque distance, no alignment) is wrong for a gate that must name
a fix location."

### 13. Cross-language clone detection (general)
Detects: same logical code duplicated across language boundaries
(e.g., a Python helper reimplemented in TypeScript).
Cost: depends entirely on normalization strategy; the only tractable
zero-model approach is normalizing to a common IR before any rung runs.
Implementability: **already the architecture** -- `docs/modules/dup.md`
states every rung operates on `frob.lang`'s normalized output, making
cross-language clones structurally reachable by construction, PROVIDED
`frob.lang` actually normalizes multiple grammars to a shared node
vocabulary. This needs verification against `frob.lang`'s real coverage
(Python/TS/Rust/C/C++ per CLAUDE.md's stated language set) -- out of
this ticket's read scope (frob.lang is a separate module), flagged as a
dependency to verify, not re-derived here.
**Verdict: ADOPT is architecturally already claimed; VERIFY (not
re-research) that `frob.lang`'s node-label vocabulary is actually shared
across grammars** -- if node labels diverge per-language (e.g. Python's
"for" vs Rust's "for_expression" hashing to different R3 tokens), cross-
language matching silently fails despite the architecture supporting it
in principle. Recommend a follow-up ticket that is a *test*, not a
redesign: one cross-language clone litmus fixture (same logic, Python +
TS) run through the real pipeline, asserting a match.

### 14. Winnowing / MOSS (Schleimer, Wilkerson, Aiken 2003)
**Already adopted** -- `frob_core::winnow_fingerprints` is a direct MOSS-
style winnowing implementation (line 49). No further action.
**Verdict: ADOPT (done).**

### 15. MinHash / LSH for near-duplicate detection at scale
**Already adopted** in effect -- `frob_core::candidate_pairs` (line 102)
buckets by shared winnowed fingerprints, which is LSH-banding's
substance even if not literally MinHash-signature-based; functionally
equivalent for this corpus size. True MinHash (random permutation
signatures over shingle sets) would only matter at a scale where
`candidate_pairs`'s current bucketing degrades -- no evidence of that
here.
**Verdict: ADOPT (done, sufficient); REJECT swapping in literal MinHash**
absent a demonstrated scaling problem.

### 16. Suffix automata / generalized suffix trees (for exact/near-exact
repeated-substring detection, e.g. as used in some Type-1 detectors and
in bioinformatics-derived clone tools)
Detects: Type-1 (exact) and some Type-2 (via generalized suffix tree over
normalized token streams) repeated substrings, with all maximal repeats
found in O(n) via Ukkonen's algorithm.
Cost: O(n) construction, O(n) total repeat enumeration -- asymptotically
best-in-class for exact substring clone detection, strictly better than
winnowing for the *exact-match* case (winnowing samples a subset of
k-grams for space efficiency, trading recall for space; a suffix
automaton finds every maximal repeat exactly).
Implementability: straightforward in Rust, no model, well-understood
algorithm (Ukkonen 1995), and frob-core already builds custom kernels of
comparable complexity (Zhang-Shasha, WL-hash).
**Verdict: ADAPT.** R1/R2 currently hash whole normalized bodies (line 16
`hash_str`) rather than finding maximal repeated substrings within/across
bodies -- so a partial exact clone (same 15-line block copy-pasted into
an otherwise-different function) is invisible to R1/R2 today and only
caught if it happens to survive into R4's winnowed-fingerprint region
matching. A suffix-automaton pass over the corpus's concatenated
normalized token stream would find *every* exact repeated region
(any length, any position) in one linear pass, subsuming R1/R2's exact-
match case AND extending it to sub-symbol regions without waiting for
R4's probabilistic winnowing. Effort: medium (new Rust kernel,
generalized suffix automaton over multi-document corpus, standard
algorithm not exotic) -- worth a ticket as "R1.5: exact region clones via
suffix automaton," strictly additive, closes a real gap (R1/R2 are
whole-symbol-only right now per the code read in section 0).

### 17. Anti-unification / Plotkin's least general generalization (lgg)
Detects: not a detector -- a *generalization* operator. Given two (or more)
terms/trees, produces the most specific common template plus the
substitutions that recover each original from the template. This is
exactly the "reverse templating" the ticket asks for.
Cost: linear in tree size for first-order anti-unification (structural
recursion, generalize mismatched positions to fresh variables, memoize
repeated subterm pairs); higher for the higher-order case (see item 18).
Implementability: **directly implementable in Rust with zero model
dependency** -- classic Plotkin (1970) algorithm: walk two trees
top-down, where labels match keep the node and recurse, where they
differ (or arity differs) introduce a fresh generalization variable
bound to the pair `(subtree_a, subtree_b)`. Runs naturally over the same
node-array representation `apted_similarity` already consumes
(labels + parent-index arrays), so it is additive to the existing tree
kernel rather than a new representation.
**Verdict: ADOPT.** This is the load-bearing algorithm for the
reverse-templating deliverable (section 4). Effort: medium (new Rust
kernel `anti_unify(labels_a, parents_a, labels_b, parents_b) ->
(template_labels, template_parents, bindings_a, bindings_b)`), no
external dependency, sketch in section 4.

### 18. Higher-order anti-unification (generalizing over functions/binders,
not just first-order terms -- lambda-calculus-level lgg)
Detects: same as item 17 but for cases where the *shape of abstraction*
itself differs (e.g. one clone maps over a list with a lambda, the other
uses an explicit loop) -- catches template families first-order
anti-unification cannot express.
Cost: significantly higher; higher-order unification is undecidable in
general, higher-order anti-unification research (Cerna & Kutsia and
related recent work) uses restricted fragments (patterns, or bounded
unification rank) to stay tractable.
Implementability: substantial research-grade implementation effort for
a capability frob's use case (templating *already-matched* R3-R5 clone
pairs, which by construction share the same control-flow shape post-
canonicalization) mostly does not need -- R3's control-flow normalization
already collapses the loop-vs-map distinction into a canonical form
before anti-unification would ever see it.
**Verdict: REJECT (not worth the complexity given R3 pre-normalization
already narrows the gap higher-order AU exists to close).** First-order
AU (item 17) over R3-canonicalized trees captures the realistic case.

### 19. Parameterized clone reporting (template + per-instance bindings
as the user-facing report shape, distinct from the algorithm in item 17)
Detects: n/a -- a reporting/UX concern, not a detection technique.
Implementability: trivial given item 17's output -- `ClonePair` already
carries `alignment: tuple[tuple[int,int],...]`; extending `CloneReport`
groups with a `template: CloneTemplate` field (generalized source text +
named holes + per-region binding table) is additive pydantic-model work.
**Verdict: ADOPT**, described in section 4, depends only on item 17.

### 20. Extract-function suggestion synthesis (turn a clone group + its
anti-unified template into a concrete "extract this into function `f`"
patch suggestion, including parameter list synthesis)
Detects: n/a -- code-transformation-suggestion capability, downstream of
items 17-19.
Cost: linear given the template (assign one parameter per generalization
variable, order by first occurrence, infer a type hint only if
`frob.lang` already carries type info for both occurrences -- degrade to
untyped `Any`-style placeholder otherwise rather than guessing).
Implementability: fully mechanical from the anti-unification template;
the honest limit is naming (frob can synthesize `f(x0, x1, ...)` but
cannot know a good name -- report that as a TODO placeholder in the
suggestion, never a guessed name presented as fact) and safety (a
suggested extraction is advisory text in the DUP001 message, never an
auto-applied refactor -- consistent with "gate is conformance, not
autofix" in every other frob gate).
**Verdict: ADOPT**, advisory-text-only, sketch in section 4.

### 21-26. Process/meta deliverables
Covered directly in sections 3-6 below (ranked shortlist, reverse-
templating sketch, meta-test matrix design, ticket tree, and the
gate-integration gap already surfaced in section 0). Each is
dispositioned by being written, not by a verdict tag -- there is no
REJECT/ADOPT for a required section of this document.

## 3. Ranked shortlist of upgrades (effort estimates)

1. **Wire DUP001/DUP002 into `frob.gates.__init__`.** (section 0's gap 26)
   Not a new technique -- everything above is inert until this lands.
   Effort: small-medium (rules already pure functions; wiring + fixture
   tests). Highest priority: every other item on this list is pointless
   work until the gate actually fires.
2. **Wire `frob dup --probe` CLI flag to the existing, already-working
   `probe_equivalence` (R6).** Effort: small. R6 is fully implemented and
   sitting unreachable (T-0041 debt, confirmed still true).
3. **R1.5: suffix-automaton exact-region clone pass** (item 16). Effort:
   medium. Closes a real, confirmed gap: R1/R2 are whole-symbol-only.
4. **Anti-unification kernel + reverse-templating report** (items 17,
   19, 20). Effort: medium-large, highest product value (directly serves
   the "impossible to be a lazy developer" goal from CLAUDE.md -- a
   violation message that hands you the extracted function, not just a
   percentage).
5. **Close the R5 CFG/DFG fidelity gap** (items 7/8): replace/augment the
   co-occurrence proxy fallback with real control-flow edges from
   `frob.lang` wherever available, keep the proxy only as the genuine
   fallback for symbols it cannot parse (matches R4's already-established
   two-tier pattern). Effort: medium, contingent on `frob.lang` exposing
   the needed edges (verify before scoping).
6. **DECKARD-style structural characteristic-vector pre-filter** (item 4)
   and **Oreo-style metric-ratio pre-filter** (item 6, non-ML half only).
   Effort: small each, additive to candidate generation, no gate-behavior
   risk (pre-filters only prune candidate pairs, never add false
   positives).
7. **Cross-language litmus fixture** (item 13) -- a test, not a feature:
   confirms the claimed cross-language architecture actually matches
   node vocabulary across two `frob.lang` grammars. Effort: small.
8. **NiCad size-ratio pre-filter** (item 2's one adoptable idea). Effort:
   trivial, fold into existing candidate-pairs stage.

Explicitly NOT on this list (see per-item REJECT above, not omitted --
Oreo's classifier, CCLearner, ASTNN, FA-AST's GNN, CodeBERT embeddings,
higher-order anti-unification, literal MinHash, generic AST fingerprints,
SourcererCC's block index, full PDG subgraph isomorphism).

## 4. Reverse-templating design sketch

Goal: a clone group (`ClonePair`s already produced by R3/R4/R5) becomes
`template + per-instance bindings + suggested extraction signature`,
built entirely from anti-unification (item 17) over kernel outputs
frob-core already produces -- no new detection, only a new synthesis
stage consuming existing `ClonePair.alignment` + `frob.lang.symbol_tree`.

**Inputs already available:**
- `frob.lang.symbol_tree(path, span)` + `_common.flatten_tree` -- the
  same `(labels, parents)` node-array pair `apted_similarity` already
  consumes (`_pipeline/_callgraph.py::_apted_similarity_for_pair`, confirmed in
  section 0).
- `ClonePair.alignment: tuple[tuple[int,int],...]` -- matched line/
  statement pairs, already computed by the verifying rung.

**New kernel** (Rust, `frob-core`, data-in/data-out, no IO -- matches
every existing kernel's contract):
```rust
fn anti_unify(
    labels_a: Vec<String>, parents_a: Vec<i64>,
    labels_b: Vec<String>, parents_b: Vec<i64>,
) -> (Vec<String>, Vec<i64>, Vec<(usize, usize)>, Vec<(usize, usize)>)
// returns: template (labels, parents) with fresh "$hole_N" labels at
// divergence points, plus binding-index pairs (template hole -> a-node,
// template hole -> b-node)
```
Walk both trees top-down in lockstep (same recursion shape
`build_postorder`/`keyroots` already use): where `labels_a[i] ==
labels_b[j]` and arity matches, emit the shared node and recurse into
children; on mismatch, emit `$hole_N`, record `(N, i)` and `(N, j)` as
bindings, and stop recursing on that branch (the subtrees under a hole
are exactly what differs per-instance and become the argument
expressions, not part of the template).

**Python-side model additions** (`frob.dup._models`, additive, frozen
pydantic per existing convention):
```python
class CloneBinding(BaseModel):    # frozen
    hole: int
    region: CloneRegion            # which instance, which span
    source_text: str                # the concrete subexpression, for the report

class CloneTemplate(BaseModel):   # frozen
    skeleton_text: str              # template with $hole_N placeholders, pretty-printed
    holes: tuple[int, ...]
    bindings: tuple[tuple[CloneBinding, ...], ...]  # one tuple per group member
    suggested_signature: str        # e.g. "def _extracted(hole_0, hole_1): ..."
```
`CloneReport.groups` gains an optional `template: CloneTemplate | None`
(present only when anti-unification succeeded and the hole count is
below a sanity ceiling -- e.g. >50% of nodes being holes means "not
really a clone, don't synthesize a useless template," `Err` back to a
plain `ClonePair` report with no template rather than emitting noise).

**Signature synthesis:** one parameter per distinct hole, ordered by
first occurrence in the template's preorder walk; parameter name is
`hole_N` unless `frob.lang` carries a type-annotated identifier at that
position in *both* instances with the *same* name (then reuse it --
cheap common-case win, e.g. both clones call the parameter `items`).
Type hint attached only when both instances' bound subtrees carry the
same static type from `frob.lang`'s type info; otherwise omitted, never
guessed. This is advisory text embedded in the DUP001 message
("candidate extraction: `def _shared(hole_0: int, hole_1: list[str]) ->
...`") -- never an auto-applied patch, consistent with every other frob
gate being conformance-only.

## 5. Meta-test design: (clone-type x language x rung) exhaustiveness matrix

Mirrors T-0158's capability-matrix pattern (`frob vet`'s dangerous-
operations registry): a structured registry file plus one litmus fixture
pair per populated cell, and a suite that fails loudly on any claim
without a fixture.

**Registry shape** (<!-- frob:waive DOC006 reason="hypothetical proposed module name for a not-yet-built registry, the sentence itself says 'is likely stored'" -->`frob/dup/_matrix.py` or a TOML table, matching how
T-0158's registry is likely stored -- same convention, not re-derived):
rows = clone type (1: exact, 2: renamed, 3: near-miss/gapped, 4: semantic-
equivalent-different-structure); columns = `frob.lang`-supported
language (Python, TypeScript, Rust, C, C++ per CLAUDE.md's stated set);
depth = rung (R1-R7). Each populated cell declares:
```toml
[[matrix]]
clone_type = 3
language = "python"
rung = "r4"
fixture = "tests/fixtures/dup/type3_python_r4/"
claim = "gapped near-miss clone via winnow+APTED"
```
**Litmus fixture per cell:** a directory with two source files (or two
spans in one file) that ARE a clone of the declared type in the declared
language, plus a `expected.json` asserting `find_clones` returns a
`ClonePair` with `rung == "r4"` and `similarity >= threshold`. For
Type-4/R5-R7 cells, the fixture pair is semantically equivalent but
structurally distinct (e.g. iterative vs. recursive factorial) so a rung
that only does structural matching provably fails it and a rung with
real dataflow/behavioral comparison provably passes.

**Exhaustiveness enforcement:** a suite test (same shape as T-0158's
"capability exhaustiveness matrix" test, not reinvented) that:
1. Loads the registry, asserts every `(clone_type, language, rung)` the
   docs/rung table (`docs/modules/dup.md`'s "Catches" column) *claims* to
   catch has a matching registry row -- a claim in prose with no fixture
   row is a build failure (mirrors DRIFT001/COV001's doc-drift enforcement
   already in frob, extended to this domain-specific claim/fixture
   binding rather than a generic doc-edge).
2. For every registry row, actually runs `find_clones` (or the specific
   rung function) against the fixture and asserts the claimed rung is
   the one that fired -- catches both false claims (rung doesn't actually
   catch it) and rung creep (a *different*, unlisted rung silently catches
   it, meaning the matrix's "which rung is responsible" claim is wrong,
   which matters for DUP001's message naming the rung).
3. A new detector or rung added without a corresponding registry entry +
   fixture directory fails this suite immediately (glob-diff between
   `frob-core`'s exported kernel list / `docs/modules/dup.md`'s rung table
   and the registry rows) -- same mechanism as R3+'s `CoreUnavailable`
   check: absence is loud, never silent.
4. Language coverage gaps (e.g. no C++ Type-4 fixture) show as an empty
   cell rather than a missing test -- report as `blocked`/`todo` in the
   matrix output, not silently absent, matching this survey's own
   "no silent drops" requirement.

## 6. Proposed ticket tree (titles + one-line scope, for coordinator to file)

- **T-dup-gate-wire**: Wire `DUP001`/`DUP002` into `frob.gates.__init__`
  so `frob check` actually enforces the R1-R5 pipeline (currently only
  the legacy Type-1/2 scanner gates).
- **T-dup-probe-cli**: Add `frob dup --probe` CLI flag reaching the
  already-implemented `probe_equivalence` (R6); closes T-0041.
- **T-dup-suffix-automaton**: New `frob-core` kernel: generalized suffix
  automaton over the corpus's normalized token stream for exact
  sub-symbol repeated-region detection (R1.5), catching partial
  copy-paste clones R1/R2's whole-body-only hashing misses today.
- **T-dup-anti-unify-kernel**: New `frob-core` kernel `anti_unify`
  (Plotkin lgg over `(labels, parents)` node arrays) -- foundation for
  reverse-templating.
- **T-dup-template-report**: `CloneTemplate`/`CloneBinding` pydantic
  models + `CloneReport.groups[].template` wiring + DUP001 message
  extension with the synthesized extraction-signature suggestion,
  depends on T-dup-anti-unify-kernel.
- **T-dup-r5-real-cfg**: Verify `frob.lang`'s actual control-flow-edge
  coverage and, where available, replace the R5 co-occurrence-proxy
  fallback's use with real edges (proxy stays as genuine fallback for
  unparseable symbols, matching R4's established two-tier pattern).
- **T-dup-prefilter-vectors**: DECKARD-style structural characteristic-
  vector LSH pre-filter + Oreo-style metric-ratio pre-filter, both as
  additive candidate-pruning stages before APTED/WL-hash verification.
- **T-dup-crosslang-litmus**: One cross-language clone fixture (same
  logic in two `frob.lang`-supported languages) run through the real
  pipeline to verify the claimed cross-language architecture actually
  matches node vocabulary across grammars.
- **T-dup-matrix**: Build the (clone-type x language x rung)
  exhaustiveness matrix registry + fixture directories + the
  claim-vs-fixture enforcement suite (section 5), in the mold of
  T-0158's capability matrix.
- **T-dup-nicad-sizefilter**: Trivial size/statement-count-ratio
  pre-filter in the existing candidate-pairs stage before APTED is
  invoked (smallest-effort item on the shortlist, bundle with whichever
  prefilter ticket lands first rather than filing standalone if the
  coordinator prefers fewer tickets).

## Coverage proof (Phase 2)

Denominator: 26 enumerated universe items (1-16 detection/scalability
techniques, 17-20 abstraction/reverse-templating techniques, 21-26
required report sections/deliverables). Done: 26/26 -- every item in
section 1 has an explicit disposition in section 2 (with a verdict tag:
ADOPT/ADAPT/REJECT/ADOPT-done/VERIFY, or is directly satisfied by a later
section as noted for 21-26). Blocked: 0. Pending: 0.

Two findings surfaced by reading the actual source rather than trusting
the ticket brief's summary, recorded because the brief's premise was
partially stale: (a) real APTED (Zhang-Shasha) tree-edit verification is
already implemented and wired as R4's primary path, with Levenshtein
demoted to fallback-only; (b) R5's dataflow graph likewise has a real
primary path with the co-occurrence proxy demoted to fallback-only. The
brief's most durable debt claim -- R6/probe unwired from the CLI -- is
confirmed still true by direct search (no `probe`/`--probe` string
anywhere under `src/frob/cli*`).
