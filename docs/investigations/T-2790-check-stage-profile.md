# T-2790: profile of the top four `frob check` stages, and what is reducible

Measured in the T-2790 worktree, natives built, real repo (this checkout,
~1200 Python files, 25593 symbols / 26233 edges in the graph snapshot).
Fleet load was high while these numbers were taken (other agents landing
concurrently, LOAD 17-29, several live leases) so ABSOLUTE wall-clock
numbers below are inflated versus T-2782's quieter 274.56s cold baseline.
The RELATIVE breakdown inside each stage (which function dominates, what
fraction of the stage's own time it is) is the load-bearing result here,
not the absolute seconds -- contention stretches everything roughly
proportionally, it does not change which function is hot.

Method: called each gate function directly under `cProfile`
(`sys_gate`/`perf_gate`/`dead_symbol_gate(root, snapshot)`,
`arch_gate(root)`), using one `build_graph()`-produced `GraphSnapshot`
(built once, 12.7s, pickled and reused across the sys/perf/dead_symbols
profiles so graph construction itself is not counted against them).
`frob check --json`'s own per-stage numbers from T-2782 are the
authoritative real-world figures; this document's job is to explain WHERE
inside each of those numbers the time goes.

## Summary answer to the ticket's central question

**Yes.** Three of the four stages independently re-derive data that
another part of the system has already computed once, and the
re-derivation is not merely "uncached" -- in two cases (perf,
dead_symbols) a *disk-backed, content-hash-keyed cache for exactly this
computation already exists in this codebase* and these stages simply do
not benefit from it, because of a process-boundary the cache's memo layer
does not cross. That is the real lever, and it does not require choosing
between soundness and speed: the cache is keyed on content hash and the
value cached is a pure function's deterministic output.

## archgate (45.44s in the real check; profiled 236.34s alone under load)

```
1199 calls  _analyze_one_file           232.49s cumulative
1199 calls  _run_python_checks          222.80s cumulative
2925 calls  _py_build_module             73.40s cumulative  (31%)
34495 calls _py_build_function           70.53s cumulative
4.8M calls  _py_collect_body_events      35.19s cumulative
18.4M calls _iter_own_scope              30.68s tottime      (largest single tottime)
```

`_py_build_module`/`_py_build_function`/`_py_collect_body_events`/
`_iter_own_scope` together are the per-function metrics extraction that
feeds long-function/god-class/deep-nesting/cyclomatic checks -- a pure,
per-file, per-function walk over the tree-sitter tree with no cross-file
dependency at all.

**This exact walk already has a golden-tested Rust replacement that was
built and never wired in.** T-1222 (archived, done) delivered
`frob_core.py_function_metrics(source: bytes)`, a byte-for-byte parity
port of `_py_max_nesting`/`_py_cyclomatic`/`_py_collect_body_events`'s
combined output (T-1222's own done report: "golden test against this
repo's own `src/frob/arch/_python.py`... 0 mismatches", 5 passing parity
tests still present at `tests/unit/test_arch_python_native.py`). Its own
done report states the Python path it replaces is "measured 97 pct of
archgate's own cost, `_py_build_module` alone 31 pct" -- this profile
reproduces that 31% figure exactly (73.40s / 236.34s = 31.1%) on a repo
that has grown since. Checked directly: `frob_core.py_function_metrics`
has zero call sites anywhere under `src/frob/` (`git grep` for
`py_function_metrics` under `src/` returns nothing) -- the kernel is
exported from `frob_core` and covered by tests, but `_py_build_function`/
`_py_build_module` still run the pure-Python path in production. This is
the "shipped but not reachable" pattern this repo has hit before
(catalogued-is-not-enforced): work landed, verified, documented, and
never wired to the caller it was built to replace.

Whole-program or not: **mixed**. The per-function metrics extraction
(long-function, god-class-by-method-count, deep-nesting, cyclomatic) is
purely per-file/per-function -- genuinely incremental-safe, cacheable by
file content hash, no cross-file dependency. `_check_high_coupling`,
`_near_duplicate_cluster` (already natively accelerated per T-0953), and
the concurrency-model/lock-ordering/async-hazard checks (`_concurrency_
model.py`, `_lock_ordering.py`, `_async_hazards.py`, `_shared_state_
race.py`) are genuinely whole-program (a caller in file B can create a
concurrency hazard whose other half lives in file A) and cannot be
diff-scoped without becoming unsound. The dominant COST measured here is
in the per-file-safe portion, not the whole-program portion.

## perf (59.63s in the real check; profiled 297.39s alone under load)

```
1 call    perf_rules                  214.77s cumulative
1 call    duplicate_spawn_violations   85.51s cumulative
1211 calls _perf_gate_parse_files      85.07s cumulative  (29%)
1211 calls parse_file -> extract()     84.95s cumulative
```

`_perf_gate_parse_files` re-parses and re-extracts every file via
`frob.lang.parse_file`, the SAME function `build_graph()` already called
once to build the `GraphSnapshot` this gate receives as an argument.
`parse_file` has a persistent, content-hash-keyed sqlite artifact cache
for the raw tree-sitter parse itself (T-0414), so this is not re-reading
and re-lexing from scratch -- but `parse_file`'s `extract()` step (the
structured symbol/comment walk over that tree) is only memoized via
`@memoize_per_run` (T-0423/T-0410), a process-lifetime, in-memory cache.
Every gate here is dispatched as its own OS process
(`_ProcessJob(perf_gate, ...)`, confirmed in `gates/__init__.py`), so
`perf_gate`'s process gets a cheap disk-cache hit on the raw parse but
still pays the full `extract()` walk cost itself, because the process
that ran `build_graph()`'s `extract()` calls and populated that in-memory
memo is a DIFFERENT process that has already exited.

Whole-program or not: **mostly per-file**. `hotpath_smell_violations`,
most of `perf_rules`' per-symbol checks, and `_loop_effects` operate one
file/one function at a time. `duplicate_spawn_violations`'s cross-file
`_entry_occurrences` dedup is the one genuinely whole-program piece here
(it needs every file's spawn-site entries to detect a duplicate across
files) -- small relative to the parse/extract cost, not this stage's
bottleneck.

## dead_symbols (34.08s in the real check; profiled 290.38s alone under load)

```
65 calls (1/package)  build_reference_graph   195.02s cumulative
65 calls               _parse_package          87.67s cumulative (30%)
1190 calls             parse_file->extract()   87.51s cumulative
```

Same root cause as perf, reached through a different call path:
`build_reference_graph`/`_parse_package` re-parses and re-extracts every
file per PACKAGE (65 packages, ~1190 `parse_file` calls) via the same
`frob.lang.parse_file`, hitting the same disk-level parse cache but
missing the same in-process-only `extract()` memo that `build_graph()`'s
own earlier run already paid for and discarded when its process exited.
This is a second, independent instance of the identical structural gap
`perf` has -- confirming the ticket's suspicion directly: dead_symbols
and perf both redundantly re-derive the SAME already-computed extraction,
for the same reason, and a single fix closes both.

Whole-program or not: **genuinely whole-program**, and this is the
strongest case of the four. Whether symbol X is dead depends on every
caller in the codebase; a new call site anywhere can revive a symbol this
analysis previously called dead. This cannot be soundly diff-scoped --
skipping unchanged files' *reachability conclusions* would be unsound.
What CAN be shared without touching soundness is the per-file
*extraction* (`parse_file`/`extract()`'s output, i.e. what symbols/calls
a file contains) that reachability is computed FROM -- the aggregation
(who calls whom, is X reachable) still needs to run over the complete,
current set of per-file facts every time; only the re-derivation of
those per-file facts on files that have not changed is the waste.

## sys (69.78s in the real check; profiled 366.47s alone under load)

```
1 call     _selfaudit_violations          290.86s cumulative
1 call     check_self_conformance         281.45s cumulative
1199 calls scan_file_capabilities         162.37s cumulative (44%)
2374 calls _python_resolved_candidates    137.18s cumulative
1187 calls _python_binding_capabilities    71.57s cumulative
```

This is a structurally different case from the other three:
`scan_file_capabilities`'s Python-aware resolution
(`_python_binding_capabilities`/`_python_local_wrapper_capabilities`/
`_build_py_alias_table`/`_resolve_py_expr`) is built on the stdlib `ast`
module (`ast.walk`, `ast.iter_child_nodes` both appear directly in this
profile), NOT tree-sitter, and NOT `frob.lang.parse_file`. It is a THIRD,
independent parse mechanism from the tree-sitter path `build_graph`/
`perf`/`dead_symbols`/`archgate` all use in one form or another, and it
has **no cache at all** -- not the disk-backed content-hash cache
(T-0414), not the per-run memo (T-0423), nothing: `path.read_bytes()`
followed by an `ast`-based walk runs unconditionally on every one of
sys's 1199 files, every single invocation. Checked directly:
`_capability_scan.py`/`_capability_python.py` contain no `memoize`,
`lru_cache`, or content-hash-cache reference of any kind.

Whole-program or not: **genuinely whole-program**, and the strongest
case among the four along with dead_symbols. Capability flow (does data
reaching an `eval`/`exec`/network/filesystem sink originate from an
untrusted channel) is a cross-file dataflow property by nature -- a
wrapper function in file A that calls an exec-ish sink in file B, or a
capability re-exported through several hops, requires seeing the whole
graph, matching T-2782's own framing of this family. As with dead_
symbols, though, the underlying PER-FILE local fact (what capability
tokens does this one file's text/AST expose, before any cross-file
resolution) is a pure, deterministic function of file content and is a
legitimate cache target even though the aggregation stays whole-program.
Because there is no cache here today at all (not even the cheap
disk-backed one the other two paths already have), this is the largest
single opportunity by raw stage time (69.78s, the largest of the four)
but also the largest lift: it needs a cache built from scratch on a
different parse technology, not an extension of an existing one.

## What this rules out

- Nothing here proposes skipping a whole-program aggregation step, or
  narrowing what any gate checks. Every proposal below is "compute this
  deterministic per-file fact once and reuse it," never "check fewer
  files" or "trust a stale conclusion."
- The T-2782 finding stands: none of this makes verification safe to run
  OUTSIDE the land lock. The aggregation step (the genuinely
  whole-program part) still must run against the current, fully-merged
  tree every time.
- No proposal here touches `_check_high_coupling`, the concurrency/
  lock-ordering/async-hazard family, `duplicate_spawn_violations`'s
  cross-file dedup, or dead_symbols'/sys's cross-file aggregation logic
  itself -- those stay exactly as expensive and exactly as necessary as
  they are today.

## Proposed child tickets (not implemented here, per this ticket's own scope)

1. **Wire T-1222's `frob_core.py_function_metrics` into
   `_py_build_function`/`_py_build_module`.** Already built, already
   golden-tested byte-identical to the Python path it replaces. Directly
   cuts archgate's measured 31% dominant cost. Needs: a positive-control
   test proving a planted long-function/god-class/deep-nesting violation
   still fires identically through the native path, and a real
   unbudgeted before/after `frob check` run showing an identical finding
   count.

2. **Extend the existing parse-artifact disk cache (T-0414,
   `_parse_file_with_artifact_cache`) to persist `extract()`'s structured
   output, not just the raw tree-sitter parse.** This is the single
   fix that would help BOTH perf and dead_symbols (measured ~85s and
   ~87.5s of redundant cross-process re-extraction respectively,
   corroborating T-1344/T-0410's docstring-recorded architecture gap
   directly): both stages already hit the raw-parse cache and still pay
   the full extraction walk because that layer is process-lifetime only
   (T-0423) and each gate is its own OS process. Content-hash-keyed, so
   this is a pure cache extension with no soundness change -- needs a
   positive control (planted symbol change must still invalidate the
   cache entry and produce the correct extraction) and a before/after
   identical-finding-count run.

3. **Build a content-hash-keyed cache for `scan_file_capabilities`'s
   ast-based resolution (sys's dominant cost, currently uncached at any
   layer).** Larger lift than #2 (new cache, not an extension of an
   existing one; different parse technology). Should be scoped
   separately and is lower-confidence on effort-to-win ratio until
   someone sizes it -- filed as its own ticket rather than folded into
   #2's scope.

None of these three touch the whole-program aggregation logic in any of
the four stages. All three are "compute a deterministic per-file fact
once, reuse it," which is a caching change, not a soundness change --
each child ticket's own acceptance criteria must still include the
identical-finding-count control this ticket's constraints require.

Filed (drafts, renumber at land, parent=T-2790):

- T-2799 -- wire `frob_core.py_function_metrics` into
  archgate's per-function metrics walk (item 1 above).
- T-2797 -- extend the parse-artifact disk cache to persist
  `extract()`'s output, closing the shared gap behind both perf's and
  dead_symbols' redundant re-extraction (item 2 above).
- T-2798 -- size a content-hash cache for sys's ast-based
  capability scan, currently uncached at any layer (item 3 above).
