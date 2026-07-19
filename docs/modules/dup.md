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
bounded subset (see `frob.dup._pipeline._smt_translate`'s accepted node
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
`frob.dup._core.exact_regions` and `frob.dup._pipeline._region_groups`.
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
```

Reported `ClonePair`s use `rung="r1.5"`, `similarity=1.0` (every match is
exact by construction), and a narrowed `CloneRegion` span covering just
the matched token window -- not the whole symbol, same posture as R4's
region-narrowing.

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

class CloneReport(BaseModel):   # frozen
    groups: tuple[tuple[ClonePair, ...], ...]
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

class DupError(ErrorSet):
    CoreUnavailable      = "frob-core native extension is not installed"
    NotPure              = "Probe target has effects; observational probing refused"
    CacheCorrupt         = "dup cache unreadable; delete .frob/dup.db to rebuild"
    HoleCeilingExceeded  = "anti-unification template is >50% holes; not a meaningful generalization"
```

`frob.toml`:

```toml
[dup]
threshold = 0.85          # DUP001 similarity floor
min_tokens = 40           # ignore trivial bodies
cache_entries = 200000    # LRU cap on pairwise verdicts
region_kernel = false     # R1.5 exact-region kernel opt-in (needs enforce=true too)
region_min_tokens = 15    # R1.5 floor below which a region match is not reported
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
<!-- frob:describes frob-core/src/lib.rs::frob_core -->

Every `#[pyfunction]`/`#[pymodule]` item is the crate's Python-facing public
API (a PyO3 export is public even without a Rust `pub` keyword -- frob's
Rust extractor treats the export attribute as public for this reason). The
thin `frob.dup._core` Python shim wraps each of these; see the Python-side
descriptions above.

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
- `frob_core` -- the `#[pymodule]` registration entry that exports the above
  to Python.

## Anti-unification (Plotkin lgg)

<a id="anti-unification-plotkin-lgg"></a>
<!-- frob:describes frob.dup._core.anti_unify -->
<!-- frob:describes frob.dup.AntiUnifyTemplate -->

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
DUP001 messages) and T-0287 (type-hole generalization) build on; neither is
implemented by this kernel itself.

## Gate integration

- DUP001 (error): diff introduces a clone of a pre-existing symbol at or
  above threshold. Message names the existing symref, similarity, rung,
  and the waiver form (`frob:waive DUP001 reason="..."`).
- DUP002 (warn): clones internal to the diff itself (two new copies).
- The pre-work sweep (`frob ticket start`) reuses the same pipeline
  scoped to the ticket, replacing the old advisory dup+xref sweep with
  the mechanized check.

## Dependencies and integration points

- `frob.lang` (normalized tokens/trees), `frob.graph` (digests, purity
  facts, snapshot), `frob.gitio` (diff), `frob-core` (kernels),
  `frob.fuzz` generators for R6 (docs/modules/fuzz.md).
- CLI: `frob dup [--all|--base REF] [--probe] [--json]`.
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
  (`frob_core.wl_hash`, new kernel) over a co-occurrence proxy for each
  function's def-use graph (`_build_dataflow_graph`'s deviation note --
  no real CFG/DFG exists, so this connects every identifier token within
  a heuristic statement chunk and labels by "immediately followed by `=`"
  as a def/use proxy).
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
  `src/frob/__main__.py`'s `_add_dup_parser`) is the CLI surface: it
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
  function-declaration walk (`frob.lang._common.iter_cpp_functions`) that
  used to be duplicated, with slightly different depth handling, in both
  `frob.ast.cpp` and `frob.dup._legacy`.
- `frob.lang.symbol_tree(path, span)` / `frob.lang._common.flatten_tree` --
  new this pass, feeding `frob-core`'s `apted_similarity` (see R4 above)
  and R5's real dataflow graph.

`grep -rn "frob\.ast" src/ tests/` (excluding the `SOURCES.txt` build
artifact) returns nothing.

## Public API reference

<a id="public-api"></a>
<!-- frob:describes frob.dup.find_clones -->
<!-- frob:describes frob.dup.probe_equivalence -->
**`find_clones`/`probe_equivalence`**: see the "Public API" code block
above for signatures. `find_clones` runs the R1-R5 ladder; `probe_equivalence`
is R6, opt-in and separate from the gate path.

<a id="rung-r7"></a>
<!-- frob:describes frob.dup._pipeline.probe_smt_equivalence -->
**`probe_smt_equivalence`**: R7, opt-in bounded-SMT formal-equivalence
check for tiny int/bool functions (`z3-solver`, optional).

<a id="pipeline"></a>
<!-- frob:describes frob.dup._pipeline.touched_refs -->
**`touched_refs`**: symrefs in a `GraphSnapshot` whose span overlaps a
`Diff` hunk -- the "new side" restriction `find_clones` uses for the
DUP001 gate path.

<a id="rust-core"></a>
<!-- frob:describes frob.dup._core.core_available -->
<!-- frob:describes frob.dup._core.INSTALL_HINT -->
<!-- frob:describes frob.dup._core.r3_canonical_hash -->
<!-- frob:describes frob.dup._core.winnow_fingerprints -->
<!-- frob:describes frob.dup._core.candidate_pairs -->
<!-- frob:describes frob.dup._core.tree_edit_similarity -->
**`frob.dup._core`**: thin `Result`-returning shims over the `frob_core`
native extension (see "Rust core" above) -- `core_available` gates every
other call; a missing extension is `Err(DupError.CoreUnavailable)`, never
a silent downgrade.

<a id="rung-r4"></a>
<!-- frob:describes frob.dup._core.apted_similarity -->
**`apted_similarity`**: real Zhang-Shasha tree-edit-distance similarity
between two exported `frob.lang` subtrees -- R4's verification metric.

<a id="rung-r5"></a>
<!-- frob:describes frob.dup._core.wl_hash -->
**`wl_hash`**: Weisfeiler-Lehman graph-kernel hash of a def-use/control-
flow adjacency -- R5's fingerprint.

<a id="gate-integration"></a>
<!-- frob:describes frob.dup._rules.DUP001 -->
<!-- frob:describes frob.dup._rules.DUP002 -->
See "Gate integration" above for what DUP001/DUP002 report.

<a id="dup-error"></a>
<!-- frob:describes frob.dup.DupError -->
<a id="clone-region"></a>
<!-- frob:describes frob.dup.CloneRegion -->
<a id="clone-pair"></a>
<!-- frob:describes frob.dup.ClonePair -->
<a id="clone-report"></a>
<!-- frob:describes frob.dup.CloneReport -->
<a id="dup-stats"></a>
<!-- frob:describes frob.dup.DupStats -->
<a id="dup-config"></a>
<!-- frob:describes frob.dup.DupConfig -->
<a id="probe-verdict"></a>
<!-- frob:describes frob.dup.ProbeVerdict -->
See the "Public API" code block above for `DupError`/`CloneRegion`/
`ClonePair`/`CloneReport`/`DupStats`/`DupConfig`/`ProbeVerdict` field
shapes.

<a id="caching"></a>
<!-- frob:describes frob.dup._cache.get_fingerprint -->
<!-- frob:describes frob.dup._cache.put_fingerprint -->
<!-- frob:describes frob.dup._cache.get_verdict -->
<!-- frob:describes frob.dup._cache.put_verdict -->
See "Caching (content-addressed + LRU)" above -- these four functions are
the `.frob/dup.db` read/write surface `find_clones` uses.

<a id="legacy-scanner"></a>
<!-- frob:describes frob.dup._legacy.DupError -->
<!-- frob:describes frob.dup._legacy.CodeFragment -->
<!-- frob:describes frob.dup._legacy.CloneGroup -->
<!-- frob:describes frob.dup._legacy.DupResult -->
<!-- frob:describes frob.dup.find_duplicates -->
The pre-smart-dup Type-1/Type-2 scanner (`frob.dup._legacy`), kept
verbatim in behavior and re-exported as `frob.dup.find_duplicates` for
`frob check`'s dup stage and the `frob dup` CLI -- see "frob.ast
retirement" above for what changed under the hood (parsing now goes
through `frob.lang.raw_tree`, not the deleted `frob.ast` package).
