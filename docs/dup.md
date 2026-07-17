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
| R3 | canonicalized-AST subtree hash: alpha-rename, literal abstraction, commutative-operand ordering, control-flow normalization (for/while desugar, early-return vs if-else) | restructured dressing, same shape (PyCharm's level) | cheap |
| R4 | winnowed fingerprints (Moss) + Deckard-style characteristic vectors under LSH; candidate pairs verified by tree edit distance (APTED) with statement alignment | gapped/near-miss clones, statements inserted or deleted | moderate; Rust kernel |
| R5 | Weisfeiler-Lehman graph-kernel hashing over the def-use/control dependence graph of each function | reordered-but-dataflow-identical logic (beyond PyCharm) | moderate; Rust kernel |
| R6 | observational equivalence: probe candidate pure functions with identical inputs drawn from the SHARED invariant-respecting generators (docs/fuzz.md) and compare outputs | true semantic clones -- different algorithm, same behavior | opt-in (`--probe`); Python orchestrated |

R6 is honest about limits: full Type-4 equivalence is undecidable; probing
gives high-confidence evidence, not proof. A bounded-SMT rung (translate
tiny pure int/bool functions to Z3 and check equivalence formally) is a
recorded research item, not a commitment.

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
    rung: str                   # "r3" | "r4" | "r5" | "r6"
    alignment: tuple[tuple[int, int], ...]   # matched line pairs

class CloneReport(BaseModel):   # frozen
    groups: tuple[tuple[ClonePair, ...], ...]
    stats: DupStats             # fingerprinted, cache_hits, pairs_verified

class DupError(ErrorSet):
    CoreUnavailable = "frob-core native extension is not installed"
    NotPure         = "Probe target has effects; observational probing refused"
    CacheCorrupt    = "dup cache unreadable; delete .frob/dup.db to rebuild"
```

`frob.toml`:

```toml
[dup]
threshold = 0.85        # DUP001 similarity floor
min_tokens = 40         # ignore trivial bodies
cache_entries = 200000  # LRU cap on pairwise verdicts
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
  every non-dup frob feature keep working pure-Python.
- The crate is compute-only: it takes serialized token/tree/graph inputs
  and returns fingerprints/distances; all IO, caching policy, and git
  awareness stay in Python. This keeps the FFI surface data-in/data-out
  and trivially testable from both sides.
- Errors cross the boundary as values (PyO3 -> a thin shim -> ErrorSet),
  matching the lithos CoreFailure pattern.

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
  `frob.fuzz` generators for R6 (docs/fuzz.md).
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
  wants R6 (docs/dup.md's "opt-in `--probe` path"); wiring an actual
  `frob dup --probe` CLI flag is out of `frob.dup`'s scope and reported
  to the coordinator.
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
- **`find_duplicates`** (the old Type-1/2 scanner) is preserved verbatim
  in `frob.dup._legacy` and re-exported from `frob.dup.__init__`
  unchanged, so `frob check`'s dup stage and `frob dup` CLI keep working.
- **DUP001/DUP002** are pure functions in `frob.dup._rules`:
  `DUP001(report: CloneReport, touched: frozenset[str], threshold: float)
  -> tuple[Violation, ...]` (error severity: one side of the pair is a
  touched/new symbol, the other pre-existing) and `DUP002` with the same
  signature (warn severity: both sides touched). `touched` is produced by
  `frob.dup.touched_refs(snapshot, diff)`. Not wired into
  `frob.gates.__init__` -- that integration is out of this ticket's scope
  per the dispatch instructions.
