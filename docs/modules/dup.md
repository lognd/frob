# frob.dup (smart) -- semantic duplication detection

One sentence: a rung-ladder of clone detectors -- from token clones up to
behavioral equivalence -- run as an incremental, content-addressed pipeline
with Rust kernels, and enforced as a gate (DUP001) so introducing a
duplicate is a build failure pointing at the thing to reuse.

Supersedes the current Type-1/Type-2 `frob.dup` when the re-platform onto
`frob.lang` lands (Phase 7). Cross-language by construction: every rung
operates on `frob.lang`'s normalized output, so a Python helper
reimplemented in TypeScript is still a clone.

## The rungs

| Rung | Technique | Catches | Cost |
|---|---|---|---|
| R1 | exact token hash | copy-paste | trivial |
| R2 | alpha-renamed token hash | rename-only clones | trivial |
| R1.5 | generalized suffix array + LCP over the corpus's normalized token stream (a `frob-core` Rust kernel); off by default even when R3+ is enabled | exact repeated SUB-REGIONS: a copy-pasted block sitting inside two otherwise-different symbols, invisible to R1/R2's whole-body hashing | opt-in (`[dup].region_kernel`); Rust kernel |
| R3 | canonicalized-AST subtree hash: alpha-rename, literal abstraction, commutative-operand ordering, control-flow normalization (for/while desugar, early-return vs if-else) | restructured dressing, same shape (PyCharm's level) | cheap |
| R4 | winnowed fingerprints (Moss) + Deckard-style characteristic vectors under LSH; candidate pairs verified by real tree edit distance (Zhang-Shasha, a `frob-core` Rust kernel over actual node structure) | gapped/near-miss clones, statements inserted or deleted, within-statement restructuring | moderate; Rust kernel |
| R5 | Weisfeiler-Lehman graph-kernel hashing over a real def-use/control-flow graph built from `frob.lang`'s statement nodes | reordered-but-dataflow-identical logic (beyond PyCharm) | moderate; Rust kernel |
| R6 | observational equivalence: probe candidate pure functions with identical inputs drawn from the SHARED invariant-respecting generators (docs/modules/fuzz.md) and compare outputs | true semantic clones -- different algorithm, same behavior | opt-in (`--probe`); Python orchestrated |
| R7 | bounded-SMT: translate tiny, single-return, int/bool, straight-line functions to a Z3 formula and check equivalence by UNSAT (optional `z3-solver` dep) | formally-proved equivalence over the whole input domain, for the bounded subset | opt-in; degrades to `Err` without `frob[smt]` |

R6 is honest about limits: full Type-4 equivalence is undecidable; probing
gives high-confidence evidence, not proof. R7 is real for its explicitly
bounded subset (see `frob.dup._pipeline._smt._smt_translate`'s accepted node
set) -- it is a formal proof only within that subset, not a general
equivalence checker; anything outside the subset is refused
(`Err(SmtUnsupported)`), never silently approximated.

## R1.5: exact-region kernel (T-0193)

<a id="rung-r1-5"></a>

R1/R2 hash WHOLE symbol bodies (`frob.dup._pipeline._r1_hash`/`_r2_hash`),
so a copy-pasted block sitting inside two otherwise-different functions is
invisible to them -- neither whole-body hash collides when the
surrounding code differs. R1.5 closes that gap with a generalized suffix
array (Manber-Myers rank-doubling construction) plus Kasai's LCP array
over the WHOLE corpus's concatenated, R2-normalized token stream (one
"document" per fingerprinted symbol, a unique per-document sentinel
between documents so no match crosses a symbol boundary) --
`frob_core.exact_regions` (`frob-core/src/lib.rs`), wired through
`frob.dup._core._exact_regions` and `frob.dup._pipeline._fingerprint._region_groups`.
This finds every MAXIMAL exact-token-match region of length
`>= [dup].region_min_tokens` in one pass -- a strict superset of R1/R2's
exact-match recall, extended to sub-symbol regions, without waiting for
R4's probabilistic winnowing to happen to catch the same block.

**Off by default, independent of `[dup].enforce`.** Turning on the
whole-symbol rung ladder (`[dup].enforce = true`) does not by itself pay
for the extra suffix-array pass -- both `[dup].enforce` AND
`[dup].region_kernel = true` must be set for R1.5 to run in the gate path
(`frob.gates.dup_gate`'s `_dup_config`). This keeps a default `frob check`
exactly as fast as before this rung existed.

```toml
[dup]
enforce = true
region_kernel = true    # opt-in: also off by default
region_min_tokens = 15  # floor below which a region match is not reported
region_run_cap = 200    # per-run pair-emission guard, see below
```

Reported `ClonePair`s use `rung="r1.5"`, `similarity=1.0` (every match is
exact by construction), and a narrowed `CloneRegion` span covering just
the matched token window -- not the whole symbol, same posture as R4's
region-narrowing.

## `[dup].native_rungs`: gating R3/R4/R5 independently of `enforce` (T-0974)

R3/R4/R5 (`DupConfig.native_rungs_enabled`, default `True` at the
`DupConfig` class level -- see its docstring for why) run one `frob-core`
native call per fingerprinted symbol each (canonical hash, winnowed
k-gram set, WL-hash respectively). At this repo's own whole-snapshot
scale that native-call-per-symbol cost is the dominant driver of
`find_clones`'s COLD wall time (no `.frob/dup.db` fingerprint cache yet --
the common case in a fresh worktree, docs/guides/worktree-natives-
artifact): T-0399 first measured `[dup].enforce=true` alone blowing past
the ~150s single-stage foreground budget, and T-0974 reproduced the same
blowout and pinned it to these three rungs specifically.

Getting `[dup].enforce=true` to actually fit the budget took two rounds.
First, splitting R1/R2 (cheap, pure-Python) from R3-R5 via this flag
wasn't sufficient by itself -- profiling the R1/R2-only path uncovered a
genuine cross-process DEADLOCK (not just slowness): `find_clones` used to
take `derived_state_write_lock` unconditionally around its whole rung
ladder (T-1224 moved this down to the individual cache writes -- see
below), but the "clones" gate runs in
a `ProcessPoolExecutor` worker (T-0415) while `frob check`'s main process
holds the derived-state lock SHARED for the whole run, and the write
lock's same-process reentrancy check couldn't see across the pool's fork
boundary. T-0982 fixed that (the pool owner now stamps
`FROB_DERIVED_LOCK_HELD_KEYS` before construction; see
docs/modules/process.md). With that landed, T-0974 re-measured:
`native_rungs=true` (the full R1-R5 ladder) still exceeds a 300s
foreground cap cold and stays opt-in; `native_rungs=false` (R1/R2 only)
measures ~34-44s cold / ~20-22s warm for the clones stage alone,
comfortably inside the ~90s per-stage budget. `[dup].enforce=true` now
ships ON by default in this repo's own `frob.toml` with `native_rungs`
left off (`false`) -- R1/R2 clone detection is live by default; R3-R5's
deeper semantic ladder stays opt-in until a follow-up makes its cold cost
affordable too (an incremental per-file re-index or a narrower default
snapshot scope -- not attempted this pass, see T-0974's Done report).
`dup_gate` still fails closed with DUP003 (ERROR) if `frob-core` is
missing while `[dup].enforce=true`, regardless of `native_rungs` -- that
check gates the whole rung ladder's availability, not just the native
subset.

```toml
[dup]
enforce = true          # R1/R2 on by default (T-0974); cheap even cold
native_rungs = false    # opt-in: R3/R4/R5 (native-call-per-symbol cost)
```

**Run-size guard (`[dup].region_run_cap`, T-0273).** Emitting every
occurrence pair within one equal-token run is O(k^2) in the run size `k`
(`emit_run_pairs` in `frob-core/src/lib.rs`) -- a reviewer demonstrated
2000 identical 20-token documents sharing a block producing 1,999,000
pairs in 17.5s. A real monorepo with thousands of near-identical
generated/boilerplate symbols sharing a block `>= region_min_tokens`
would hit the same wall. `region_run_cap` (default 200) bounds `k` per
run: a run larger than the cap only pairs its first `region_run_cap`
occurrences with each other, capping per-run cost at O(region_run_cap^2)
no matter how many more times the block repeats. Truncation is signaled,
never silent (the T-0193-recall-bug lesson) -- `frob_core.exact_regions`
returns `(regions, truncated)`, and `frob.dup._pipeline._fingerprint._region_groups`
logs a WARN naming `[dup].region_run_cap` when at least one run was
capped.

## Granularity: regions, not just functions

Matches are region-to-region, where a region is a whole symbol OR any
contiguous statement subsequence inside one -- so all three shapes are
first-class: function-vs-function, function-vs-subsection (someone inlined
a helper's logic mid-function), and subsection-vs-subsection (the same
eight lines buried in two unrelated functions).

Mechanically this falls out of the rungs rather than being bolted on:
winnowed fingerprints (R4) are computed over sliding token windows and are
position-independent by construction; R3 hashes EVERY statement-block
subtree, not just function roots; APTED alignment reports the matched
subrange on each side. The `min_tokens` floor is what keeps region
matching from drowning in trivial three-line hits. R5/R6 remain
whole-function rungs (dependence graphs and behavioral probes need a
complete unit) -- region hits found by R3/R4 near a function boundary are
promoted to a whole-function R5 check automatically.

Enforcement is conformance, same as every other gate: a region hit at or
above threshold is a DUP001/DUP002 violation whose message names both
regions and the extraction target ("extract into a shared helper or waive
with reason") -- never an advisory report.

<!-- frob:invariant INV-011 -->

## Pipeline

1. **Fingerprint** (incremental): per changed file, compute R1-R5
   fingerprints from `frob.lang` output; store in `.frob/dup.db` keyed by
   symbol `body` digest -- content-addressed, so a fingerprint is never
   stale and never recomputed for an unchanged body.
2. **Candidates**: LSH buckets + fingerprint collisions produce pairs.
3. **Verify**: tree edit distance on candidates -> similarity percent and
   statement alignment; R6 probing only on demand for pairs the graph
   knows are effect-free.
4. **Report/gate**: `frob dup` renders groups; DUP001 fires when the diff
   introduces a symbol whose best match against a PRE-EXISTING symbol
   exceeds `[dup].threshold`.

## Helper-inlining triage (T-0288)

`frob arch` pushes toward many small private helpers; that is good
architecture and bad news for R1-R5, which all compare whole symbol
bodies -- two functions with identical logic split into differently-named
private helpers now hash/compare as different call skeletons. Two fixes,
both triage-only (source is never rewritten; every `ClonePair.region` still
points at the real symbol's real span):

1. **Call-graph-aware inlining.** Before fingerprinting, `_body_tokens_for_symbol`
   resolves the symbol's calls to PRIVATE (leading-underscore, module-local,
   never re-exported) helpers via `frob.graph.callgraph` and splices their
   `body_tokens` into the comparison unit -- a bounded closure:
   depth-limited (`DupConfig.inline_max_depth`, default 3), node-count-capped
   (`DupConfig.inline_max_nodes`, default 12), cycle-guarded (a visited set;
   mutual recursion never loops), and PUBLIC-API-stopping (`build_call_graph`
   never records an edge to a public callee, so the closure has nothing to
   walk past one). `DupConfig.min_tokens` is checked AFTER inlining, so a
   thin call-site wrapper whose real logic lives one hop away is measured
   by that real logic, not by the wrapper's own token count. Disable with
   `[dup].inline_calls = false`.
2. **Helper-population pass.** Over-splitting spawns families of
   near-identical TINY private helpers, which the whole-symbol `min_tokens`
   default (40) would otherwise silently skip entirely. `find_helper_clones`
   restricts the snapshot to private/module-local FUNCTION/METHOD symbols
   and reruns the full rung ladder with `DupConfig.helper_min_tokens`
   (default 8) in place of `min_tokens`, so an over-split family is caught
   on its own terms.

The call-graph substrate itself (`frob.graph.callgraph`) is a standalone,
reusable module -- not dup-specific -- so future arch work (recursion
detection, T-0290) consumes the same call-resolution logic rather than
re-deriving it. See docs/modules/graph.md's "Call graph" section for its
API.

## Caching (content-addressed + LRU)

Two layers, one rule each:

- **Correctness comes from content addressing.** Every cache key is built
  from body digests: fingerprints keyed by `digest`, pairwise verdicts
  keyed by `(min(d1,d2), max(d1,d2), method, corpus_epoch)`. A body edit
  changes the digest, which IS the invalidation -- no staleness logic
  exists to get wrong.
- **Boundedness comes from LRU.** Pairwise verdicts grow quadratically in
  the worst case, so the verdict table carries `last_used` and is evicted
  LRU beyond `[dup].cache_entries` (default 200k rows). Fingerprints are
  linear in repo size and are pruned only when their file leaves the
  graph. In-process, hot digest lookups sit behind `functools.lru_cache`;
  the Rust kernels keep their own small LRU (lru crate) for repeated
  tree-edit subproblems within a run.

R6 verdicts additionally key on `corpus_epoch` (bumped when generator
definitions change) so probe results outlive runs but never outlive the
generators that produced them.

**Locking granularity (T-1224).** `find_clones` no longer wraps its whole
rung ladder in `frob.process._lock.derived_state_write_lock` -- profiling
showed a standalone rebuild (e.g. `frob dup`, not nested inside a `frob
check` run) taking that lock EXCLUSIVE for the entire computation (~34s+
even warm), which serialized every concurrent reader (e.g. a sibling
agent's `frob check`, holding the derived-state lock SHARED) against it
for that whole duration -- observed as a ~240s `flock` wait under
profiling with four concurrent agents. The rung computation itself only
READS the snapshot and the fingerprint/verdict cache; the only on-disk
mutation is `frob.dup._cache.put_fingerprint`/`put_verdict`. The lock is
now taken individually inside those two functions, around just the
`INSERT`/`DELETE` + `commit()` calls, so a standalone rebuild only blocks
concurrent readers for the brief duration of an actual cache write, not
for the whole clones stage. The nested (already-under-`frob check`)
same-process no-op behavior from T-0918/T-0982 is unchanged -- it is
consulted at each of these smaller call sites instead of once at the top.

## Public API

```python
# frob/dup/__init__.py (post re-platform)
def find_clones(snapshot: GraphSnapshot, cfg: DupConfig,
                diff: Diff | None = None) -> Result[CloneReport, DupError]
    # diff=None scans the whole snapshot; diff given restricts "new side"
    # to touched symbols (the DUP001 gate path).
def probe_equivalence(a: str, b: str, snapshot: GraphSnapshot,
                      budget_s: float) -> Result[ProbeVerdict, DupError]
    # R6; refuses symbols not provably effect-free (Err(NotPure)).

class CloneRegion(BaseModel):   # frozen -- a symbol or a slice of one
    ref: str                    # symref
    span: tuple[int, int]       # 1-based lines; whole symbol = full span

class ClonePair(BaseModel):     # frozen
    left: CloneRegion
    right: CloneRegion
    similarity: float           # 0..1 from the verifying rung
    rung: str                   # "r1" | "r2" | "r1.5" | "r3" | "r4" | "r5" | "r6"
    alignment: tuple[tuple[int, int], ...]   # matched line pairs

class CloneMatchGroup(BaseModel):   # frozen
    pairs: tuple[ClonePair, ...]
    template: CloneTemplate | None    # None when reverse-templating didn't apply

class CloneReport(BaseModel):   # frozen
    groups: tuple[CloneMatchGroup, ...]
    stats: DupStats             # fingerprinted, cache_hits, pairs_verified

def anti_unify(labels_a, parents_a, labels_b, parents_b,
              ) -> Result[AntiUnifyTemplate, DupError]
    # Plotkin lgg over the same (labels, parents) node arrays
    # apted_similarity consumes; Err(HoleCeilingExceeded) when the
    # generalized template would be >50% $hole_N placeholders.

class AntiUnifyTemplate(BaseModel):   # frozen
    labels: tuple[str, ...]           # template node labels; "$hole_N" at divergence
    parents: tuple[int, ...]          # same node-array shape as apted_similarity's input
    bindings_a: tuple[tuple[int, int], ...]   # (hole_id, a-side node index)
    bindings_b: tuple[tuple[int, int], ...]   # (hole_id, b-side node index)

def build_group_template(root: Path, pairs: tuple[ClonePair, ...],
                         ) -> CloneTemplate | None
    # Reverse-templating report over a clone group's distinct members
    # (see "Reverse-templating report" below); never raises.

class CloneBinding(BaseModel):   # frozen -- one hole's concrete side
    hole: int
    region: CloneRegion
    source_text: str            # structural skeleton of the bound subtree

class CloneTemplate(BaseModel):   # frozen -- a group's generalized report
    skeleton_text: str           # readable template, "$hole_N" at divergence
    holes: tuple[int, ...]
    bindings: tuple[tuple[CloneBinding, ...], ...]   # one tuple per member
    suggested_signature: str     # advisory extraction signature text

class DupError(ErrorSet):
    CoreUnavailable      = "frob-core native extension is not installed"
    NotPure              = "Probe target has effects; observational probing refused"
    CacheCorrupt         = "dup cache unreadable; delete .frob/dup.db to rebuild"
    NoGenerator          = "no frob.fuzz Arbitrary generator for a probe parameter"
    SmtUnavailable       = "z3-solver not installed; install with: uv pip install frob[smt]"
    SmtUnsupported       = "function body is outside R7's bounded int/bool subset"
    HoleCeilingExceeded  = "anti-unification template is >50% holes; not a meaningful generalization"
```

`frob.toml`:

```toml
[dup]
threshold = 0.85          # DUP001 similarity floor
min_tokens = 40           # ignore trivial bodies
cache_entries = 200000    # LRU cap on pairwise verdicts
native_rungs = false      # R3/R4/R5 opt-in (native-call-per-symbol cost, T-0974)
region_kernel = false     # R1.5 exact-region kernel opt-in (needs enforce=true too)
region_min_tokens = 15    # R1.5 floor below which a region match is not reported
region_run_cap = 200      # R1.5 per-run pair-emission guard (T-0273)
```

## Rust core (frob-core)

The R3 canonicalizer, winnowing, LSH bucketing, WL-kernel hashing, and
APTED tree edit distance live in a `frob-core` PyO3 crate built with
maturin (abi3 wheels; ../lithos is the workspace/layout reference). Design
rules:

- **No pure-Python fallback implementations.** Two implementations of one
  kernel is the duplication disease this module exists to kill. If
  `frob_core` is not importable, dup rungs R3+ return
  `Err(CoreUnavailable)` with the install command in the log; R1/R2 and
  every non-dup frob feature keep working pure-Python. `INSTALL_HINT` is
  that logged command.
- The crate is compute-only: it takes serialized token/tree/graph inputs
  and returns fingerprints/distances; all IO, caching policy, and git
  awareness stay in Python. This keeps the FFI surface data-in/data-out
  and trivially testable from both sides.
- Errors cross the boundary as values (PyO3 -> a thin shim -> ErrorSet),
  matching the lithos CoreFailure pattern.

### frob-core kernels (the PyO3-exported surface)

<!-- frob:describes frob-core/src/lib.rs::r3_canonical_hash -->
<!-- frob:describes frob-core/src/lib.rs::winnow_fingerprints -->
<!-- frob:describes frob-core/src/lib.rs::candidate_pairs -->
<!-- frob:describes frob-core/src/lib.rs::tree_edit_similarity -->
<!-- frob:describes frob-core/src/lib.rs::apted_similarity -->
<!-- frob:describes frob-core/src/lib.rs::anti_unify -->
<!-- frob:describes frob-core/src/lib.rs::wl_hash -->
<!-- frob:describes frob-core/src/lib.rs::exact_regions -->
<!-- frob:describes frob-core/src/lib.rs::resolve_call_edges -->
<!-- frob:describes frob-core/src/lib.rs::called_names -->
<!-- frob:describes frob-core/src/lib.rs::ordered_called_names -->
<!-- frob:describes frob-core/src/lib.rs::referenced_names -->
<!-- frob:describes frob-core/src/lib.rs::unresolved_exempt_names -->
<!-- frob:describes frob-core/src/lib.rs::near_duplicate_indices -->
<!-- frob:describes frob-core/src/lib.rs::frob_core -->

Every `#[pyfunction]`/`#[pymodule]` item is the crate's Python-facing public
API (a PyO3 export is public even without a Rust `pub` keyword -- frob's
Rust extractor treats the export attribute as public for this reason). The
thin `frob.dup._core` Python shim wraps each of these; see the Python-side
descriptions above.

T-1220 added a sixteenth export, `extract_tree_python` -- a python-only
tree-extraction kernel, unrelated to clone detection or the call graph;
see docs/modules/lang.md#extraction-api for its own description. Noted
here only because `frob_core`'s `#[pymodule]` registration function
(`m.add_function(wrap_pyfunction!(extract_tree_python, m)?)?;`) is this
crate's single shared entry point every export threads through.

T-1220 added a seventeenth export, `extract_tree_rust` -- the rust-language
companion to `extract_tree_python` (same registration function, same
`frob_core` pymodule); see docs/modules/lang.md#extraction-api.

T-0930 added five more kernels to this SAME crate/pymodule for
`frob.graph.callgraph` (not `frob.dup`) -- `resolve_call_edges`,
`called_names`, `ordered_called_names`, `referenced_names`, and
`unresolved_exempt_names`. See docs/modules/graph.md#rust-core for their
Python-side wiring (`frob.graph._core`), including the disclosed finding
that only `resolve_call_edges` is actually dispatched to by default --
the other four are parked (correct, parity-tested, exported) but
measured net-slower than pure-Python at this repo's real per-symbol call
granularity, so no Python shim calls them.

T-0953 added one more kernel to this SAME crate/pymodule for
`frob.arch._python` (not `frob.dup` or `frob.graph`) --
`near_duplicate_indices`, archgate's `_near_duplicate_cluster`
body-similarity clustering (docs/audits/check-performance.md's T-0951/
T-0953 remediation logs). Unlike T-0930's five kernels, this one IS wired
as the default path (`_near_duplicate_cluster_native` in
`src/frob/arch/_python.py`, falling back to the original pure-Python
`difflib` loop when `frob_core` is unavailable): batching ONE marshal per
same-signature group (not per pairwise comparison) let this repo's real
group sizes (up to several dozen members, O(n^2) pairwise comparisons per
group) amortize the fixed PyO3 marshaling tax that sank T-0930's
per-symbol dispatch, measuring ~2.6x faster (median 2.49s -> 0.97s
thread_time across this repo's own 67 real same-signature groups) with 0
parity mismatches against `difflib.SequenceMatcher.ratio()`.

- `r3_canonical_hash` -- R3 canonical fold of an alpha-renamed token stream
  into one stable hex digest (equal-shape bodies collide).
- `winnow_fingerprints` -- R4 Moss-style winnowed k-gram fingerprints,
  position-independent, for region-granular matching.
- `candidate_pairs` -- LSH bucketing that yields only the fragment pairs
  sharing enough fingerprints to be worth an exact compare.
- `tree_edit_similarity` -- statement-sequence edit similarity plus the
  aligned index pairs, used for the near-miss floor and region narrowing.
- `apted_similarity` -- R4 Zhang-Shasha tree-edit distance over real subtree
  structure (parent-index arrays), normalized to a similarity score.
- `anti_unify` -- Plotkin least-general-generalization over the same node
  arrays: a lockstep top-down walk emitting shared nodes where two trees
  agree and `$hole_N` at each divergence; see the "Anti-unification
  (Plotkin lgg)" section below.
- `wl_hash` -- R5 Weisfeiler-Lehman graph-kernel hash over a def-use/control
  -flow graph, collapsing reordered-but-dataflow-identical logic.
- `exact_regions` -- R1.5 generalized-suffix-array + LCP pass over the
  corpus's concatenated normalized token stream, returning every maximal
  exact-match region of length `>= min_len` across (or within) documents.
- `near_duplicate_indices` -- archgate's body-similarity clustering
  (T-0953): pairwise Ratcliff/Obershelp similarity (a statement-for-
  statement port of `difflib.SequenceMatcher.ratio()`, autojunk included)
  over one same-signature group's normalized body-fingerprint strings,
  returning the sorted indices with at least one same-group partner
  scoring `>= threshold`.
- `frob_core` -- the `#[pymodule]` registration entry that exports the above
  to Python.

## Anti-unification (Plotkin lgg)

<a id="anti-unification-plotkin-lgg"></a>
<!-- frob:describes src/frob/dup/_core.py::anti_unify -->
<!-- frob:describes src/frob/dup/_models.py::AntiUnifyTemplate -->

`anti_unify` (T-0194, docs/modules/dup-sota-survey.md section 4, item 17)
is the anti-unification kernel: given two `(labels, parents)` node arrays
-- the same representation `apted_similarity` already consumes, from
`frob.lang.symbol_tree` + `_common.flatten_tree` -- it produces the
least-general generalization (Plotkin 1970): a template that keeps every
node the two trees agree on and replaces each point of disagreement with a
fresh `$hole_N` placeholder.

**Algorithm**: a lockstep top-down walk of both trees, in the crate's
`anti_unify_core` (Rust, `frob-core/src/lib.rs`). At each position `(a,
b)`: if the labels match AND the child counts match, keep the shared node
and recurse pairwise into children (source order, same as `build_postorder`
uses); otherwise -- different label, or different arity -- emit `$hole_N`
at this position, record `(N, a)` in `bindings_a` and `(N, b)` in
`bindings_b`, and stop recursing (everything under a hole is exactly what
differs per-instance, so it belongs to the binding, not the template). Hole
numbers are assigned in preorder emission order, so the same input pair
always produces the same template -- deterministic and stable across runs.

**HOLE-CEILING sanity**: if the resulting template is more than 50% `$hole_N`
nodes by count, `anti_unify` returns `Err(DupError.HoleCeilingExceeded)`
instead of a template -- too little shared structure survived for the
result to be a meaningful generalization, and the caller should fall back
to treating the pair as a plain (non-generalized) clone match rather than
emit a near-useless "template" that is almost all holes. Both-empty inputs
generalize to an empty, zero-hole template; exactly-one-empty input always
exceeds the ceiling (nothing shared).

**PyO3 boundary**: matching every other kernel in this crate, `anti_unify`
never raises across the FFI boundary -- the `#[pyfunction]` wrapper returns
`(ok: bool, template_labels, template_parents, bindings_a, bindings_b)`; the
Python shim (`frob.dup._core.anti_unify`) turns `ok == False` into
`Err(DupError.HoleCeilingExceeded)` and `ok == True` into
`Ok(AntiUnifyTemplate(...))`.

This is the foundation T-0195 (reverse-templating report:
`CloneTemplate`/`CloneBinding` models, extraction-signature synthesis in
DUP001 messages, described below) and T-0287 (type-hole generalization)
build on.

## Reverse-templating report

<a id="reverse-templating-report"></a>
<!-- frob:describes src/frob/dup/_template.py::build_group_template -->
<!-- frob:describes src/frob/dup/_models.py::CloneTemplate -->
<!-- frob:describes src/frob/dup/_models.py::CloneBinding -->
<!-- frob:describes src/frob/dup/_models.py::CloneMatchGroup -->

T-0195 (docs/modules/dup-sota-survey.md sec 4): a synthesis stage over the
`anti_unify` kernel that turns a clone group's already-detected `ClonePair`s
into a human-readable report -- "these N functions share this template,
differing only at these holes" -- rather than just a similarity percentage.
No new detection; `frob.dup._pipeline._fingerprint._clone_report` calls
`build_group_template` once per group and attaches the result as
`CloneMatchGroup.template`, `None` when reverse-templating did not apply.

**Multi-member groups (fold, not just pairwise)**: `build_group_template`
finds every distinct `CloneRegion` referenced across a group's pairs, then
folds Plotkin lgg across them incrementally -- member 0 lgg member 1, that
result lgg member 2, and so on. The fold works because `$hole_N` placeholder
labels never collide with a real node label, so folding a hole against real
structure keeps it a hole (correctly narrowing the shared skeleton as more
members disagree at that position, never re-widening it). Per-member
bindings are then recovered by re-anti-unifying the final folded template
against each member individually: the folded template's shared nodes match
every member's tree exactly (they came from structure every member shares),
and its hole positions are visited in the same deterministic preorder order
each time `anti_unify` runs the same left-hand template against a new
right-hand tree, so hole ids line up identically across every member without
threading state through the fold by hand. A 2-member group is the trivial
case of this same fold (one iteration).

**Literal source rendering**: `CloneTemplate.skeleton_text` and
`CloneBinding.source_text` render the exact literal source characters, sliced
from `frob.lang.TreeNode.span` byte offsets (T-0327) against the member's raw
file bytes -- not a structural `label(child, child, ...)` approximation.
`_template._render_literal` walks the folded template and a member's tree in
lockstep, re-stitching the original text between children so whitespace and
formatting the parser drops from `TreeNode.label` still round-trips into the
rendering; a hole stops descent and renders as its `$hole_N` placeholder
instead of the member's concrete text. `CloneTemplate.suggested_signature`
reuses the survey's "reuse the identifier when both instances agree on a
name" nicety: when every member's bound text for a hole is the same single
plain identifier, that identifier names the parameter; otherwise it falls
back to the positional `hole_N` name (T-0481, see T-0195's Done report in
tickets-archive.md for the original follow-up this closes). It remains
advisory text embedded in DUP001's message, never an auto-applied patch,
consistent with every other frob gate being conformance-only.

**Failure is silent-to-None, never raised**: any recovery failure --
a member's subtree unavailable (unparseable file, stale span), `frob_core`
not installed, or the hole-ceiling sanity check tripping at any fold step
-- makes `build_group_template` return `None`. Callers report the group's
plain `pairs` with no template in that case, per the survey's "Err back to
a plain ClonePair report with no template rather than emitting noise" rule.

### Type-hole classification (T-0287)

<!-- frob:describes src/frob/dup/_template.py::_classify_type_vars -->

Not every hole is a value the survey's base design assumes -- some divergences
are TYPE ANNOTATIONS: the same algorithm written once over `int` and once
over `str`. `_template._is_type_position` recognizes a hole's bound node as
a type position via either of two rules (T-0495 added the second): (1) its
immediate parent is a real type-annotation WRAPPER node
(`_template._TYPE_WRAPPER_LABELS`: python's `type` node -- `def f(a:
int)` parses `int` as `type -> identifier` -- and typescript's
`type_annotation`); or (2) the node's OWN tree-sitter FIELD NAME (as seen
from its parent) is a type field (`_template._TYPE_FIELD_NAMES`: `"type"`
and `"return_type"`) -- rust/c/cpp's shape, which places the type node as
a direct, unwrapped sibling with no wrapper label at all (e.g. rust's
`parameter` node has a `type` field alongside its `pattern` field; rust's
`function_item` has a separate `return_type` field; c/cpp's
`parameter_declaration`/`function_definition` both use `"type"` for
either position). A hole qualifies as a TYPE hole only when EVERY group
member's bound node sits in such a position (the ticket's "consistency
guard": a hole that is type-shaped in some members and a plain value in
others stays an ordinary value hole, never a half-right generic).

Two type holes whose per-member bound-text sequence agrees exactly (the
same concrete types recur at both positions, in the same member order --
e.g. a parameter annotation and the return annotation it matches) are
unified into ONE type variable rather than two independent ones, since they
are provably the same abstracted type. Type variables are named `T0`, `T1`,
... in first-appearance order (`CloneTemplate.type_params`).

A classified hole renders as its type-variable name directly in
`skeleton_text` (`def f(x: T0) -> T0: ...`) instead of a bare `$hole_N`
placeholder, and `CloneBinding.type_var` names it per binding (`None` for an
ordinary value hole). `suggested_signature` gains a `TN = TypeVar("TN")`
preamble line per distinct type parameter; the extracted-function parameter
list itself is synthesized only from the remaining VALUE holes (a type hole
is not a call-site argument).

**Cross-language coverage (T-0495)**: rust/c/cpp place a type node as a
direct, unwrapped sibling distinguished only by tree-sitter FIELD NAME
(e.g. rust's `parameter` node's `type` field), which `frob.lang.TreeNode`
did not carry before T-0495 (label + children + span only, no field
names). T-0495 added `TreeNode.field` (the node's own tree-sitter field
name, populated by `frob.lang._common.export_tree` via
`Node.field_name_for_child`) and extended `_is_type_position` with the
field-name rule above, so rust type-hole classification is now real,
verified against actual `.rs` fixtures
(`tests/unit/test_dup_template.py::TestTypeHoleClassificationRust`): a
rust clone pair with consistent type annotations proposes a shared type
variable; one whose only real divergence is a value position does not.
C has its own litmus fixture too
(`tests/unit/test_dup_template.py::TestTypeHoleClassificationC`) proving
its shape (a `parameter_declaration`/`function_definition` both use
field `"type"` -- unlike rust, c has no separate `"return_type"` field).
Cpp shares c's grammar shape for this construct (verified directly
against its parse) but has no dedicated litmus fixture of its own yet --
not fixed here, filed as a follow-up rather than silently assumed to
work.

## Exhaustiveness matrix (T-0199)

`frob.dup._exhaustiveness` extends the T-0158 capability-matrix mold to
duplicate detection: a single-source `RUNG_SPECS` registry names, per
rung, which clone type(s) in the classic Roy/Cordy taxonomy (Type-1 exact,
Type-2 renamed, Type-3 near-miss, Type-4 semantic) it is designed to
catch. `dup_matrix()` cross-products every `(rung, clone_type)` pair that
follows from `RUNG_SPECS` against every supported language
(`LANGUAGES` -- python/typescript/rust/c/cpp); every resulting cell is
either `DUP_CLAIMS`-backed by a real, reused litmus fixture proving the
rung fires on that language, or `DUP_MATRIX_EXCUSES`-backed by a specific
written reason it does not (yet). `unclaimed_cells()` is the gate
condition: empty means every claimed-or-excusable cell is accounted for.
`tests/test_dup_exhaustiveness.py` is the drift-lock -- adding a rung or
widening a `claimed_clone_types` entry without a firing fixture fails the
suite immediately, before any new detector work lands (the T-0187/T-0158
acceptance bar this ticket was scoped against).

The registry is honest about two gaps it found rather than papering over
them (both filed as T-draft-d6bca168, not fixed here -- out of T-0199's scope,
which excludes `frob-core/**`):

- **R3 currently cannot be distinguished from R2 by any fixture.**
  `frob.dup._pipeline._fingerprint._fingerprint_symbol` feeds `r3_canonical_hash` the
  same `_r2_normalize` output R2 hashes -- no literal abstraction, no
  commutative-operand ordering, no for/while control-flow desugaring is
  implemented, despite `frob-core/src/lib.rs::r3_canonical_hash`'s
  docstring assuming the caller already did that work. Verified directly:
  a for-loop/while-loop pair computing the same accumulation produces
  different r2-normalized token streams, so R3 never independently fires.
- **R1-R4 are only proven cross-rung within python today; R5 is now
  proven cross-language (T-0494, updating the earlier "only python"
  claim).** `tests/test_dup_cross_lang.py` runs the SAME
  accumulator-with-clamp logic written once in Python
  (`compute_total`) and once in TypeScript (`computeTotal`) through the
  real pipeline: R1-R3 never bucket the pair together (they bucket on
  literal token vocabulary the two grammars do not share -- a real,
  still-open gap), but R5 -- which buckets on `_real_dataflow_graph`'s
  structural def/use labels, not literal tokens -- WL-hash-collides the
  pair at similarity=0.88, at every threshold tested (0.9 down to 0.1).
  This followed directly from T-0487's `_KEYWORDS` fix (TypeScript's
  `let`/`const` no longer mis-labeled as identifiers), which also
  proved R5 fires python/rust (`tests/test_dup.py::
  TestCrossLanguageR5WithLet`, `DUP_CLAIMS` r5/rust in
  `frob.dup._exhaustiveness`). No rust/c/cpp litmus fixture proves R2-R4
  cross-language yet, and no typescript `DUP_CLAIMS` entry exists
  alongside the rust one (filed as a follow-up, not fixed here --
  `src/frob/dup/_exhaustiveness.py` is out of T-0494's declared scope).
  R6/R7 ARE structurally python-only (`_load_python_callable` resolves
  to an importable Python callable; `Err(NotPure)` for every other
  language) -- a real limit, not a missing-fixture gap.

## Gate integration

- DUP001 (error): diff introduces a clone of a pre-existing symbol at or
  above threshold. Message names the existing symref, similarity, rung,
  the group's suggested extraction signature when `CloneMatchGroup.template`
  is present (`; candidate extraction: def _extracted(hole_0, ...): ...`),
  and the waiver form (`frob:waive DUP001 reason="..."`).
- DUP002 (warn): clones internal to the diff itself (two new copies).
- The pre-work sweep (`frob ticket start`) reuses the same pipeline
  scoped to the ticket, replacing the old advisory dup+xref sweep with
  the mechanized check.

## Check-stage summary is waiver-aware (T-0375)

The `frob-dup` stage of `frob check` (`frob.check._python._run_dup`) runs
the legacy `find_duplicates` scan over the whole tree, independent of
`dup_gate`'s diff-scoped DUP001/DUP002. Before T-0375 its stage summary
("`N duplicate groups`") counted every group raw, even ones a developer had
already dispositioned with a reasoned `frob:waive DUP001`/`DUP002` above one
of the group's functions -- making a written waiver pointless for the
zero-warnings headline. `_run_dup` now cross-references the obligation
graph's DUP001/DUP002 `frob:waive` edges against each group's fragment
symrefs (`path::symbol`, the same identity `frob.graph.dsl` binds a waiver
comment to).

**Full-coverage rule, not "any fragment matches" (T-0375 review fix):** a
group is excluded from the headline ONLY when EVERY one of its fragments'
symrefs is covered by a matching waiver (`_dup_group_covering_waivers`) --
not merely when any single fragment happens to be named by some waiver
elsewhere. This matters because `frob.dup._legacy`'s `_exact_groups`/
`_renamed_groups` deliberately let one symbol sit in BOTH an exact-clone
group and a DISTINCT, larger renamed-clone superset group (a renamed group
is only dropped when its whole fragment set is a subset of some exact
group's -- see `_renamed_groups`'s docstring). Concretely: if `foo` and
`bar` are exact clones of each other, and `baz` is a separate renamed
(alpha-equivalent) clone of both, `foo` sits in the exact group `{foo,
bar}` AND the renamed group `{foo, bar, baz}`. A reasoned
`frob:waive DUP001` covering `foo`+`bar` (the exact pair) correctly retires
that group -- but must NOT also retire the renamed group, because `baz` was
never reasoned about. An "any fragment symref matches" rule would silently
drop the renamed group's un-waived `baz` from the headline the moment `foo`
was waived for an unrelated pairing; full-group coverage is the only
semantics that keeps a waiver scoped to what it was actually written about.
A fully-covered group is rendered as a `note` diagnostic (`[waived:
<symref1>, <symref2>, ...]`) instead of `warning` -- never hidden, only
demoted. The summary line is `"N duplicate groups (M waived)"`, mirroring
the gates stage's `error/warning/waived` split.

Note this is a deliberately STRICTER, stage-local rule than the real
DUP001/DUP002 gate's own waiver matching: `frob.dup._rules.DUP001`/`DUP002`
never set `Violation.symref` at all, so `frob.gates._match_waiver` falls
back to its file-scoped mode for those rules (any waiver in the same file
matches). The check-stage summary's advisory count intentionally does NOT
reuse that broader file-scoped rule -- it would make one waiver anywhere in
a file silently absorb every duplicate group the file participates in, the
same class of over-exclusion this section exists to rule out.

**Nested-closure fragments: ancestor-prefix coverage (T-1035).**
`frob.dup._legacy_py._iter_functions_py` qualifies a Python function's
symbol by its FULL enclosing class/function chain (e.g. `Class.method.
closure` for a helper closure nested inside a method) -- this itself was a
T-1035 fix: qualifying only by the nearest enclosing CLASS (ignoring any
enclosing FUNCTION in between) silently collapsed two same-named nested
closures in different methods of one class to a single, ambiguous symref.
But `frob.lang`'s declared-symbol graph -- what a `frob:waive` comment's
`following`/`enclosing` binding (`frob.graph.dsl._enclosing_src`) actually
resolves against -- never tracks a nested closure as its own addressable
symbol; only top-level defs and class methods are declared symbols. A
`frob:waive DUP001` comment placed directly above the nested `def` therefore
cannot bind to the closure itself -- it binds to the nearest OUTER symbol
the graph DOES track (the enclosing method, one dotted segment short of the
fragment's own full symref). `_dup_group_covering_waivers` accounts for this
via `_dup_symref_covered`: a fragment's symref is covered either by an EXACT
match, or by any ANCESTOR qualname prefix (walking `a.b.c` -> `a.b` -> `a`)
found in the waived-symref set. This only ever changes behavior for a
symref with more than one dot (i.e. a nested-closure fragment); an ordinary
top-level function or method's symref has no ancestor prefix to fall back
to, so its exact-match requirement is unaffected.

## Dependencies and integration points

- `frob.lang` (normalized tokens/trees), `frob.graph` (digests, purity
  facts, snapshot), `frob.gitio` (diff), `frob-core` (kernels),
  `frob.fuzz` generators for R6 (docs/modules/fuzz.md).
- CLI: `frob dup [path] [--min-lines N] [--probe SYMREF_A SYMREF_B] [--json]`.
- `frob check`: DUP001/DUP002 in the gates stage.

## Implementation notes (T-0001)

First pass: R1/R2 pure Python, R3 wired through the real `frob-core`
PyO3 kernel (built and verified in this environment -- `cargo test` and
`maturin develop` both pass, `import frob_core` works). Status and
deviations, so nothing here is silently assumed done:

- **`frob-core/`** is a standalone crate + maturin project (its own
  `Cargo.toml`/`pyproject.toml`), NOT folded into `frob`'s own build
  backend -- `frob`'s `pyproject.toml` build-system stays `setuptools`
  unconditionally. Installing `frob-core` is a separate step
  (`maturin develop` from `frob-core/`, or building+installing the
  wheel); a missing Rust toolchain never blocks installing plain
  `frob`. Exposes `r3_canonical_hash`, `winnow_fingerprints`,
  `candidate_pairs`, `tree_edit_similarity` -- all data-in/data-out,
  no IO, `cargo test` covers each.
  - `tree_edit_similarity` is a statement-sequence Levenshtein
    alignment, not full APTED (the rung table names APTED explicitly).
    Catches inserted/deleted statements; does not catch within-statement
    tree restructuring. Recorded as a follow-up, not silently passed off
    as APTED.
- **`find_clones`** (`frob.dup._pipeline`) now runs the full R1-R5 ladder.
  R1 (exact hash), R2 (alpha-renamed hash), R3 (frob-core canonical hash,
  computed over the R2-normalized token stream -- see the R3
  simplification note above) all bucket-match as before. R4 wiring is new
  this pass: `frob_core.winnow_fingerprints` over the R2-normalized
  stream, `frob_core.candidate_pairs` for LSH-style candidate discovery
  (its shared-fingerprint bucketing already serves the "LSH-band
  bucketer" role named in the ticket -- a second bucketer would just be
  the same algorithm again, so none was added), then
  `frob_core.tree_edit_similarity` verification over a heuristically
  chunked statement sequence (see `_split_statements`'s deviation note in
  `_pipeline.py` -- `frob.lang` exposes no real statement boundaries, so
  chunking is a statement-starting-keyword heuristic, not a parse). R5 is
  new this pass too: a Weisfeiler-Lehman graph-kernel hash
  (`frob_core.wl_hash`, new kernel) over each function's def-use graph.
  **T-0196 update:** R5 now has two graph-construction paths, chosen per
  symbol, not one co-occurrence proxy for everything. `_real_dataflow_graph`
  walks the symbol's ACTUAL parsed subtree -- it finds the function-body
  statement container via `_BLOCK_LABELS`, walks real statement-node
  children in source order (real control flow, not token position), and
  finds each assignment's actual def/use split via `_ASSIGNMENT_LABELS`/
  `_DECLARATOR_LABELS` (a real node match, not a "next token is `=`"
  guess). This is a genuine CFG/DFG built from `frob.lang`'s parsed tree,
  for every grammar whose body/assignment shape is listed in those three
  label sets (see the coverage table below). When no such subtree is
  available (a grammar not listed, a parse failure, or a region with no
  matching block node), `find_clones` falls back to
  `_build_dataflow_graph`, the original co-occurrence proxy described
  above -- still real (it runs), still honestly documented as a proxy, now
  demoted from "the only path" to "the fallback path."

  **R5 per-language coverage (T-0196, verified against
  `src/frob/dup/_pipeline/_shared.py`'s `_BLOCK_LABELS`/`_ASSIGNMENT_LABELS`/
  `_DECLARATOR_LABELS` and `tests/test_dup_r5_multilang.py`, not
  aspirational):**

  | `frob.lang` language | Extensions | Body container matched | Def/use split matched | R5 graph |
  | --- | --- | --- | --- | --- |
  | python | `.py` | `block` | `assignment` | Real CFG/DFG (`_real_dataflow_graph`) |
  | rust | `.rs` | `block` | `let_declaration` | Real CFG/DFG (`_real_dataflow_graph`); re-assignment to an existing binding (no `let`) is not in `_ASSIGNMENT_LABELS`/`_DECLARATOR_LABELS` and falls through that statement to the proxy edge, not a hard failure of the whole graph |
  | typescript | `.ts` | `statement_block` | `assignment_expression`, `variable_declarator` (via `_DECLARATOR_LABELS`) | Real CFG/DFG (`_real_dataflow_graph`) |
  | tsx | `.tsx` | `statement_block` | `assignment_expression`, `variable_declarator` (via `_DECLARATOR_LABELS`) | Real CFG/DFG (`_real_dataflow_graph`) -- same grammar labels as typescript (`_EXTENSION_TABLE` maps `.tsx` to the `tsx` tree-sitter grammar under the same `"typescript"` `frob.lang` label); not separately covered by `tests/test_dup_r5_multilang.py`, which only exercises `.ts` |
  | c | `.c`, `.h` | `compound_statement` | `assignment_expression`, `init_declarator` (via `_DECLARATOR_LABELS`) | Real CFG/DFG (`_real_dataflow_graph`) |
  | cpp | `.cpp`, `.hpp`, `.cc`, `.hh`, `.cxx` | `compound_statement` | `assignment_expression`, `init_declarator` (via `_DECLARATOR_LABELS`) | Real CFG/DFG (`_real_dataflow_graph`) |
  | strata | `.strata` | not listed (`.strata` has no tree-sitter grammar at all -- `frob.lang.symbol_tree` returns `Err(UnsupportedLanguage)` for it, see `frob.lang`'s module docstring) | not listed | Co-occurrence proxy only (`_build_dataflow_graph`) -- `_real_dataflow_graph` cannot run without a `symbol_tree` to walk |

  A grammar row's real-CFG path is also only reached when `_find_block`
  actually finds a matching container in a given symbol's subtree; a
  region with no block node under it (an unparseable fragment, a
  non-function region R5 is asked to compare) falls back to the proxy for
  that symbol even on a grammar with real-CFG support -- the table above
  states per-grammar *capability*, not a 100%-real-path guarantee for
  every symbol in that language.
- **Region-subsection matching** falls out of R4: `tree_edit_similarity`'s
  alignment is mapped back to a line-range subset of the statement chunks
  it covers (`_region_span_for_alignment`), so a partial-body match
  reports a narrower `CloneRegion.span` than the whole symbol when the
  matched statements do not cover the whole body. The per-statement line
  number is itself an approximation (`_line_for_statement_index` spreads
  statement indices evenly across the symbol's known line span, since the
  heuristic chunker carries no real source positions) -- documented, not
  silently precise.
- **No pure-Python fallback for R3+** is honored literally: `find_clones`
  checks `frob_core` importability up front and returns
  `Err(DupError.CoreUnavailable)` for the whole call if it is missing,
  rather than silently downgrading to an R1/R2-only report.
- **`probe_equivalence`** (R6) is now real for Python-only, heuristically
  pure candidate pairs. Purity is a conservative token-blocklist check
  (`_IMPURE_TOKENS` in `_pipeline.py` -- IO, exec/eval, global/nonlocal,
  common side-effecting stdlib names); anything not certified pure still
  returns `Err(DupError.NotPure)`, matching the doc's "refuses symbols not
  provably effect-free." For a certified-pure pair, both callables are
  loaded via `importlib` from the worktree (Python only -- no
  cross-language FFI harness exists to probe a Rust/TS/C target), inputs
  are drawn from `frob.fuzz`'s Arbitrary generators keyed on the first
  function's parameter type hints (registering plain `int`/`float`/`str`/
  `bool` generators once through the public `frob.fuzz.register`
  mechanism, since `resolve` has no built-in fallback for bare scalar
  types), and outputs are compared for up to `budget_s` seconds
  (`Err(DupError.NoGenerator)` when a parameter's type has no resolvable
  generator). `probe_equivalence` is never called by `find_clones` or the
  DUP gate path -- it is only reachable from a caller that explicitly
  wants R6 (docs/modules/dup.md's "opt-in `--probe` path").
  **`frob dup <path> --probe SYMREF_A SYMREF_B`** (T-0041/T-0192, landed
  in `src/frob/app/dup_runner.py`'s `_probe` and wired in
  `src/frob/_cli_parsers/_core.py`'s `_add_dup_parser`, T-1074) is the CLI surface: it
  loads/builds the `.frob/cache.db` graph snapshot for `<path>`, resolves
  both symrefs against it, calls `probe_equivalence` with a fixed
  30-second budget, prints `EQUIVALENT`/`DIFFER`, and exits 0 for
  `EQUIVALENT`/1 for `DIFFER` or any `Err`.
  **Safety/workload contract (read before running this on an untrusted
  tree):** the purity heuristic (`_IMPURE_TOKENS`) only inspects the BODY
  TOKENS of the two probed functions -- it says nothing about the rest of
  the file. `_load_python_callable` loads each candidate with
  `importlib.util.spec_from_file_location` +
  `spec.loader.exec_module(module)`, which executes the ENTIRE module's
  top-level code (imports, module-level statements, decorators,
  `if __name__ == "__main__":` guards that happen to run at import time,
  anything), not just the two probed functions. There is no sandbox, no
  subprocess isolation, and no resource/network restriction anywhere in
  this path -- `--probe` runs arbitrary repo-controlled Python with the
  same privileges as the `frob` process itself. Only run `--probe`
  against symbols in a tree you already trust; it is not safe to point at
  unreviewed or adversarial source. The CLI `--probe` help text repeats
  this warning; do not remove it when touching the parser.
- **The `.frob/dup.db` cache** (`frob.dup._cache`) is now wired into
  `find_clones`'s hot path: R3/R4-fingerprint/R5-hash fingerprints are
  read/written keyed by body digest, and R4 pairwise verdicts (similarity
  + alignment) are read/written keyed by `(digest_pair, "r4",
  corpus_epoch=0)`, both through the existing `frob.dup._cache` API.
  Fixed a pre-existing schema bug while wiring this in: the
  `fingerprints` table's primary key was `digest` alone, not
  `(digest, rung)`, so a symbol with more than one cached rung (now
  routine, since every symbol gets an R3 hash, an R4 fingerprint set,
  *and* an R5 hash) silently clobbered all but the last rung written.
  `DupStats.cache_hits` now reports real hits on unchanged bodies across
  repeated `find_clones` calls.
- **`find_duplicates`** (the old Type-1/2 scanner) keeps its exact
  behavior in `frob.dup._legacy`, re-exported from `frob.dup.__init__`
  unchanged, so `frob check`'s dup stage and `frob dup` CLI keep working.
  It now parses through `frob.lang.raw_tree` instead of the retired
  `frob.ast` package (deleted this pass, see "frob.ast retirement"
  below) -- one grammar-loading mechanism, not a second parser stack.
- **DUP001/DUP002** are pure functions in `frob.dup._rules`:
  `DUP001(report: CloneReport, touched: frozenset[str], threshold: float)
  -> tuple[Violation, ...]` (error severity: one side of the pair is a
  touched/new symbol, the other pre-existing) and `DUP002` with the same
  signature (warn severity: both sides touched). `touched` is produced by
  `frob.dup.touched_refs(snapshot, diff)`. Not wired into
  `frob.gates.__init__` -- that integration is out of this ticket's scope
  per the dispatch instructions.

## frob.ast retirement

`src/frob/ast/` (the Python-only, hand-rolled tree-sitter wrappers
`frob.arch` and `frob.dup._legacy` used for their C/C++ and Python node
walks) is deleted. Both modules now route through `frob.lang`:

- `frob.lang.raw_tree(path)` -- the single grammar-dispatch entry point
  (`Tree`, source bytes, language label), for callers that need real
  tree-sitter `Node` access rather than `frob.lang`'s normalized shapes.
- `frob.lang.cpp_function_nodes(tree)` -- the shared C/C++
  function-declaration walk (`frob.lang._common._iter_cpp_functions`) that
  used to be duplicated, with slightly different depth handling, in both
  <!-- frob:waive DOC006 reason="frob.ast.cpp is a historical reference to a module removed before this doc pass; the sentence is describing PAST duplication, not current code" -->`frob.ast.cpp` and `frob.dup._legacy`.
- `frob.lang.symbol_tree(path, span)` / `frob.lang._common.flatten_tree` --
  new this pass, feeding `frob-core`'s `apted_similarity` (see R4 above)
  and R5's real dataflow graph.

`grep -rn "frob\.ast" src/ tests/` (excluding the `SOURCES.txt` build
artifact) returns nothing.

## Public API reference

<a id="public-api"></a>
<!-- frob:describes src/frob/dup/_pipeline/_fingerprint.py::find_clones -->
<!-- frob:describes src/frob/dup/_pipeline/_probe.py::probe_equivalence -->
**`find_clones`/`probe_equivalence`**: see the "Public API" code block
above for signatures. `find_clones` runs the R1-R5 ladder; `probe_equivalence`
is R6, opt-in and separate from the gate path.

<a id="rung-r7"></a>
<!-- frob:describes src/frob/dup/_pipeline/_smt.py::_probe_smt_equivalence -->
**`probe_smt_equivalence`**: R7, opt-in bounded-SMT formal-equivalence
check for tiny int/bool functions (`z3-solver`, optional).

<a id="pipeline"></a>
<!-- frob:describes src/frob/dup/_pipeline/_callgraph.py::touched_refs -->
**`touched_refs`**: symrefs in a `GraphSnapshot` whose span overlaps a
`Diff` hunk -- the "new side" restriction `find_clones` uses for the
DUP001 gate path.

<!-- frob:describes src/frob/dup/_pipeline/_fingerprint.py::find_helper_clones -->
**`find_helper_clones`**: see "Helper-inlining triage" above -- the
dedicated dup pass over the private-helper population, at
`DupConfig.helper_min_tokens` instead of `DupConfig.min_tokens`.

<a id="rust-core"></a>
<!-- frob:describes src/frob/dup/_core.py::core_available -->
<!-- frob:describes src/frob/dup/_core.py::INSTALL_HINT -->
<!-- frob:describes src/frob/dup/_core.py::_r3_canonical_hash -->
<!-- frob:describes src/frob/dup/_core.py::_winnow_fingerprints -->
<!-- frob:describes src/frob/dup/_core.py::_candidate_pairs -->
<!-- frob:describes src/frob/dup/_core.py::_tree_edit_similarity -->
**`frob.dup._core`**: thin `Result`-returning shims over the `frob_core`
native extension (see "Rust core" above) -- `core_available` gates every
other call; a missing extension is `Err(DupError.CoreUnavailable)`, never
a silent downgrade.

<a id="rung-r4"></a>
<!-- frob:describes src/frob/dup/_core.py::_apted_similarity -->
**`apted_similarity`**: real Zhang-Shasha tree-edit-distance similarity
between two exported `frob.lang` subtrees -- R4's verification metric.

<a id="rung-r5"></a>
<!-- frob:describes src/frob/dup/_core.py::_wl_hash -->
**`wl_hash`**: Weisfeiler-Lehman graph-kernel hash of a def-use/control-
flow adjacency -- R5's fingerprint.

<a id="gate-integration"></a>
<!-- frob:describes src/frob/dup/_rules.py::DUP001 -->
<!-- frob:describes src/frob/dup/_rules.py::DUP002 -->
See "Gate integration" above for what DUP001/DUP002 report.

<a id="dup-error"></a>
<!-- frob:describes src/frob/dup/_models.py::DupError -->
<a id="clone-region"></a>
<!-- frob:describes src/frob/dup/_models.py::CloneRegion -->
<a id="clone-pair"></a>
<!-- frob:describes src/frob/dup/_models.py::ClonePair -->
<a id="clone-report"></a>
<!-- frob:describes src/frob/dup/_models.py::CloneReport -->
<a id="dup-stats"></a>
<!-- frob:describes src/frob/dup/_models.py::DupStats -->
<a id="dup-config"></a>
<!-- frob:describes src/frob/dup/_models.py::DupConfig -->
<a id="probe-verdict"></a>
<!-- frob:describes src/frob/dup/_models.py::ProbeVerdict -->
<a id="clone-group"></a>
<!-- frob:describes src/frob/dup/_models.py::CloneMatchGroup -->
<a id="clone-binding"></a>
<!-- frob:describes src/frob/dup/_models.py::CloneBinding -->
<a id="clone-template"></a>
<!-- frob:describes src/frob/dup/_models.py::CloneTemplate -->
See the "Public API" code block above for `DupError`/`CloneRegion`/
`ClonePair`/`CloneMatchGroup`/`CloneReport`/`DupStats`/`DupConfig`/
`ProbeVerdict`/`CloneBinding`/`CloneTemplate` field shapes, and
"Reverse-templating report" above for `CloneMatchGroup.template`,
`CloneBinding`, and `CloneTemplate` semantics.

<a id="caching"></a>
<!-- frob:describes src/frob/dup/_cache.py::get_fingerprint -->
<!-- frob:describes src/frob/dup/_cache.py::put_fingerprint -->
<!-- frob:describes src/frob/dup/_cache.py::get_verdict -->
<!-- frob:describes src/frob/dup/_cache.py::put_verdict -->
See "Caching (content-addressed + LRU)" above -- these four functions are
the `.frob/dup.db` read/write surface `find_clones` uses.

<a id="legacy-scanner"></a>
<!-- frob:describes src/frob/dup/_legacy.py::DupError -->
<!-- frob:describes src/frob/dup/_legacy.py::CodeFragment -->
<!-- frob:describes src/frob/dup/_legacy.py::CloneGroup -->
<!-- frob:describes src/frob/dup/_legacy.py::DupResult -->
<!-- frob:describes src/frob/dup/_legacy.py::find_duplicates -->
The pre-smart-dup Type-1/Type-2 scanner (`frob.dup._legacy`), kept
verbatim in behavior and re-exported as `frob.dup.find_duplicates` for
`frob check`'s dup stage and the `frob dup` CLI -- see "frob.ast
retirement" above for what changed under the hood (parsing now goes
through `frob.lang.raw_tree`, not the deleted `frob.ast` package).
