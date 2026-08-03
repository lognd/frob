# frob check / daemon PERFORMANCE + CACHING audit

Status: 2026-07-27

MEASURE-FIRST. All numbers below are measured on this checkout
(`/home/logan/projects/frob`, ext4 `/dev/sdd` -- **NOT** `/mnt/c`; see Note 1),
via `uv run` (0.9.x source tree), not the stale 0.9.0 wheel.

## 2026-07-23 re-measurement (T-0582, third pass)

T-0582 re-verified the two items the T-0410 pass explicitly left
unverified (H4's vet multiplier, H5's selfconform double-scan) and
profiled the `refs` stage the T-0410 pass identified but never isolated
(then the 2nd-largest gate-summary dominator, 8-11s).

**Baseline this pass**, real `frob check` on this checkout (natives
built, warm caches, T-0414's `_parse` memo in place):

```
gates  [test=16.72s, refs=13.52s, perf=5.66s, archgate=7.93s,
        coverage=5.43s, pii_structural=4.62s, dead_symbols=3.41s,
        secrets=2.77s, tickets=1.96s, invariant=1.81s, sys=0.96s,
        render_lint=0.66s, protocol_summary=0.63s, registry=0.58s,
        walk_lint=0.91s, docblocks=0.30s, ...]
```

`archgate`/`sys` (H1/H2, T-0423) stay resolved (7.93s/0.96s here, in the
same near-zero range as the T-0410 re-measurement -- run-to-run variance,
not a regression). `refs` is now the clear 2nd-largest dominator behind
`test`, confirming the T-0410 pass's own prediction.

**(1) H4's vet multiplier -- RESOLVED, but not by the mechanism H4
guessed.** Direct measurement: called `scan_file_capabilities` (which
uses `raw_tree`, not `parse_file`) over every one of this repo's 592
tracked `.py` files and read `frob.lang.parse_cache_stats()` after each
run -- **1776 hits / 592 misses, i.e. exactly one real parse per unique
`(path, content)`, zero redundant re-parses**, despite `scan_file_
capabilities` internally calling `raw_tree` 3x per file (H4's original
claim). This is because T-0414 (landed between the T-0410 pass and this
one, not by T-0410 itself) generalized the per-run memo down to `frob.
lang._parse` itself -- the one chokepoint every public entry point
(`parse_file`, `raw_tree`, `extract_imports`) funnels through -- rather
than memoizing `parse_file` alone. `raw_tree` inherits the cache for
free. **Do not re-investigate H4's parse-multiplier concern; it is
closed by T-0414, confirmed here by a direct cache-stats measurement,
not an assumption.**

What the same profile DID surface: `scan_file_capabilities` itself is
CPU-heavy independent of parsing -- 592 files took 31.8s wall, of which
~23s was inside `_python_binding_capabilities`'s per-candidate needle
sweep (`_capability.py`), an O(candidates x capability-kinds x needles)
substring scan. Real work, not a caching bug, and not obviously safe to
rewrite blind -- filed as **T-0829** (renumbered on land)
rather than edited under this measurement ticket's scope discipline.

**(2) H5 (selfconform's double capability-scan) -- CONFIRMED STILL
UNFIXED.** `_observed_extended_kinds_by_node` and `_observed_all_kinds_
by_node` (`src/frob/strata/_selfconform.py:296`/`:319`) still each
independently loop the owned-file set and call `scan_file_capabilities`
separately, exactly as H5 originally described. The COST of that
duplication has changed shape since H4 got fixed: it used to mean a
double PARSE; now (post T-0414) it means a double CAPABILITY-RESOLUTION
pass instead (the real cost identified in (1) above), which is still
real -- roughly doubles the ~23s-per-592-files resolution cost across
whatever fraction of the owned-file set selfconform touches. Measured
`frob sys audit` on this checkout (286 bound files, a subset of the
full repo): 6.15s wall end to end; a cProfile pass on `check_self_
conformance` confirms `_capability.py`'s walk/visit/candidate-resolution
functions as the internal-time dominators. `src/frob/strata/_selfconform.
py` is outside T-0582's scope (`src/frob/vet/`) -- filed as
**T-0830** (renumbered on land) with the same one-scan-two-
derived-views fix direction H5 originally proposed, still valid.

**(3) `refs` stage profile (new -- never isolated before this pass).**
Isolated `ref_gate(root)` under cProfile (994 tracked files): dominated
by `_auto_inbound` (`src/frob/gates/_refs.py:502`) calling `_tokens_
reach` (`:465`) for every `(candidate, other)` pair -- an O(files^2)
nested scan, made worse by two of `_tokens_reach`'s fallback checks
themselves being O(tokens-in-file) generator scans over each file's
token set. Measured: 38.6M calls into one `token.endswith(...)` genexpr
alone (71.4s cProfile tottime), 19.5M more into a second one (23.7s),
95.9M total `str.endswith` calls -- the whole gate's cost is this one
shape, not parsing (the direct profile shows 0 `_parse` calls; refs
never touches `frob.lang`). `src/frob/gates/_refs.py` is outside
T-0582's scope -- filed as **T-0831** (renumbered on land),
fix direction: replace the O(files^2 x tokens_per_file) pairwise scan
with a once-built reverse index (basename/stem suffix -> candidate
files), turning it into roughly O(files x tokens_per_file).

**Verdict table:**

| Item | Audit claim | This pass | Disposition |
|---|---|---|---|
| H1 (archgate double-parse) | RESOLVED (T-0410 pass) | still resolved (7.93s) | no action |
| H2 (sys re-extract imports) | RESOLVED (T-0410 pass) | still resolved (0.96s) | no action |
| H4 vet multiplier | unverified, "may already be cheap" | RESOLVED (T-0414, confirmed via parse_cache_stats: 592 misses/1776 hits, 0 redundant parses) | closed, do not re-investigate |
| H4-adjacent: vet's own resolution cost | not identified (masked by H4's parse framing) | real, ~23s/592 files, algorithmic not caching | filed T-0829 (investigate, not blind-fixed) |
| H5 selfconform double-scan | unfixed | still unfixed; cost is now double-resolution not double-parse | filed T-0830 |
| refs stage | never profiled, "2nd dominator" | profiled: O(files^2) pairwise token-reach scan in `_tokens_reach`/`_auto_inbound` | filed T-0831 |

## 2026-07-21 re-measurement (T-0410, second pass)

The grounding numbers throughout this document (archgate=91.5-153.6s,
sys=77-145.3s) are **stale** -- both were mooted by T-0423's run-scoped
`@memoize_per_run` (landed after this audit's first pass, `frob.check._memo`),
which this ticket's own investigation (T-0418, closed as verify-first/no-code-
change) confirmed with a fresh measurement: current `frob check` on this
checkout shows `archgate=0.00s, sys=0.68-0.94s` -- **H1 and H2 below are
RESOLVED**, not by the fix direction each originally proposed (feeding the
gate the already-built snapshot), but by a more general per-run memo on
`build_graph`/`analyze_project` themselves that made the SECOND call (from
whichever stage) a cache hit regardless of call site. Do not re-investigate
H1/H2 as open findings; a future audit should re-verify only if `archgate`/
`sys` regress in a fresh timing line.

With H1/H2 gone, the new `frob check` stage-timing dominators (measured,
`gate-summary`'s bracketed timing) were **coverage=36-45s** and **refs=8-11s**,
everything else <5s. Profiling `coverage_gate` in isolation (`cProfile` over
a direct call, natives built) found a THIRD instance of this audit's own H4
class ("no shared single-parse pass"): `coverage_gate` -> `_cov006`'s COV006
rescue helpers (`_cov006_third_file_reachable`, `_cov006_public_wrapper_
reachable`) call `frob.lang.parse_file` ~2000+ times across one run, many
repeat calls on the SAME path across different candidate `Edge`s -- and
unlike H1/H2's `analyze_project`/`build_graph`, `parse_file` itself had NO
per-run memo at all. Worse, `_parse` (the raw tree-sitter parse, one level
below `parse_file`) already has its own content-hash cache, but `extract()`
(the symbol/comment walk over the tree) was never cached, so a repeat
`parse_file` call re-ran the full AST walk (`_walk_python`/`_common.walk`)
even on a `_parse` cache hit -- measured as ~151s of a ~156s `coverage_gate`
profile, almost entirely inside that walk.

**Fix landed this pass**: `@memoize_per_run` on `frob.lang.parse_file`
(`src/frob/lang/__init__.py`), applied via a first-call-deferred wrapper
rather than a module-level decorator to dodge a real `frob.lang`/`frob.check`
circular import (`frob.check.__init__` imports `frob.lang` at module scope;
a top-level `from frob.check._memo import memoize_per_run` in `frob.lang`
fails the instant anything imports `frob.lang` before `frob.check` finishes,
e.g. `frob.arch` -> `frob.lang`). Measured: isolated `coverage_gate` profile
155.8s -> 15.9s (~10x); real `frob check`'s `coverage` stage timing 36-45s ->
3.5-4.7s. Since `parse_file` is a single chokepoint used by every stage that
calls it (not just COV006), this generalizes automatically to any other
caller hitting the same path repeatedly in one run -- no further call-site
edits needed, matching T-0423's own design intent.

**Also landed this pass**: M6 (below) -- `.hypothesis`/`.serena` added to
`BUILTIN_SKIP_DIRS` (one-line, zero-risk per the original finding).

**Filed, not landed** (structural, follow-up tickets): H3 is now lower-
urgency (the two giants it worried about serializing are near-zero) but the
architectural gap (thread pool used for CPU-bound pure gates instead of the
process pool `perf`/`secrets`/`pii_structural`/`dup` already use) is
unchanged and will resurface the moment a new heavy gate is added to
`thread_jobs` instead of `process_jobs` -- filed as a follow-up (T-draft-
9f90cc43 at filing time; renumbered on land). H4's OTHER cited multipliers
(vet's `raw_tree`-based capability scan, which bypasses the new `parse_file`
memo entirely and may or may not still pay a real cost against `_parse`'s
own cache; H5's still-apparently-unfixed double selfconform scan) were not
re-verified this pass -- filed as a follow-up alongside profiling the new
`refs` stage dominator (T-draft-bafbce1c at filing time). Do not assume
either is fixed without a fresh profile.

## (A) REAL PROFILE -- authoritative numbers

**Full `uv run python -m cProfile -m frob check`** completed in **473.7s wall**
under cProfile. The profile's cumulative top is `_thread.lock.acquire` =
466.6s: cProfile only instruments the main thread, which spends the whole run
blocked on `ThreadPoolExecutor.result()` while the gate work runs in worker
threads cProfile does not sample. So the *authoritative* per-stage attribution
is frob's own in-gate `time.thread_time()` timing line (T-0232), captured from
the same run:

```
gates  [archgate=91.53s, sys=77.06s, perf=5.47s, pii_structural=2.11s,
        secrets=1.98s, test=1.87s, tickets=0.38s, fuzz=0.17s, doclink=0.10s,
        coverage=0.07s, docanchor=0.04s, release=0.03s, drift=0.01s,
        clones=0.00s, decisions=0.00s, invariant=0.00s, policy=0.00s]
```

**archgate = 91.5s and sys = 77.0s dominate; everything else combined < 12s.**
(These are CPU thread-times; grounding's 153s/145s were wall figures inflated
by GIL contention -- see Finding H3. Same two giants, same story.)

**Measured mechanism counts** (instrumenting `frob.lang._parse`, the single
read+tree-sitter-parse chokepoint every stage funnels through):

| Measurement | Result |
|---|---|
| `rglob("*")` over repo root | **744,961 entries, 6.1s per walk** |
| `arch._collect_files(root)` (walk+exclude-filter) | **9.1s**, keeps 1991 files |
| `arch.analyze_project` parses per source file | **exactly 2.0x** (426 `_parse` for 213 files) |
| `vet.scan_file_capabilities` parses per python file | **3.0x** (120 `_parse` for 40 files) |
| `build_graph` on a warm `.frob/cache.db` | **0 `_parse`, 213 cache hits, 0.3s** |

The `build_graph` sqlite cache is real and works (parsed=0/hits=213). **arch,
sys, vet, secrets each re-parse from cold and share nothing with it, nor with
each other.** That is the whole audit in one line.

---

## Findings (ranked within tier by measured wall-time win)

### HIGH

#### H1. archgate re-parses every file twice AND re-walks the 745k-entry tree, duplicating what build_graph already did
- **Where**: `src/frob/gates/__init__.py:3866` (`"archgate": lambda: arch_gate(st.root)`) -> `src/frob/arch/__init__.py:268` `analyze_project` -> `_collect_files` (line 55) + `_analyze_one_file` (line 165).
- **What's wrong**: `analyze_project` ignores the `GraphSnapshot` already built and cached by `run_gates` (`build_graph`, `gates/__init__.py:3734`). It (a) re-runs its own full-repo `rglob("*")` (`arch/__init__.py:59`) -- 9.1s measured, and (b) parses each source file **twice**: `raw_tree(path)` at `arch/__init__.py:201`, then again inside `_check_high_coupling` -> `extract_imports(path)` (`arch/_python.py:202`), which calls `_parse` a second time on the same bytes. Measured: 426 `_parse` calls for 213 files = 2.0x.
- **Failure scenario**: every `frob check`. archgate = 91.5s CPU. Roughly half of it is the second parse (import extraction) that `build_graph` already performed and stored as graph edges, plus a redundant 9.1s tree walk `_collect_files` duplicates from the graph build.
- **Fix direction**: pass the already-built snapshot into `arch_gate`/`analyze_project` (the gate lambda already has `st.snapshot`). Have `_check_high_coupling` read import counts from the snapshot's edges instead of calling `extract_imports`, and iterate the snapshot's file list instead of a fresh `rglob`. Bounded win: eliminate 1 of 2 parses/file + one 9s walk -> ~35-45s off archgate.

#### H2. sys gate (SYS003) re-walks the tree and re-extracts every import that build_graph already computed into the snapshot
- **Where**: `src/frob/gates/__init__.py:2782` `_sys003` -> `_sys003_one_model` (line 2751) -> `bind_code(model, root)` + `check_import_conformance(model, bound, root)`.
- **What's wrong**: `bind_code` globs design nodes against the whole repo (another full-tree walk), and `check_import_conformance` re-extracts imports from every design-bound file. The `sys` gate receives `st.snapshot` (line 3863 `sys_gate(st.root, st.snapshot)`) which **already contains 1627 resolved import edges** from `build_graph`, but SYS003 does not use them -- it re-parses imports from scratch. Measured: `sys` = 77.06s CPU; an isolated `sys_gate` against a warm snapshot with SYS003's models is where nearly all of it lives (a snapshot-only `sys_gate` with no models measured 5.6s / 0 parses).
- **Failure scenario**: every `frob check` in a repo with a `design/` dir (this repo has `design/frob.strata`). 77s per run, almost entirely redundant import re-extraction + a repo walk the graph build already did.
- **Fix direction**: feed `check_import_conformance` the snapshot's existing import edges instead of re-parsing; drive `bind_code`'s file enumeration from the snapshot's file set instead of a fresh glob-walk. Bounded win: most of 77s.

#### H3. All 17 gates share ONE ThreadPoolExecutor but are pure-Python CPU-bound, so archgate+sys GIL-serialize instead of overlapping
- **Where**: `src/frob/gates/__init__.py:3944` `_run_jobs` (`ThreadPoolExecutor(max_workers=max(1, len(jobs)))`); same pattern in `check/__init__.py:280` `_run_tasks_concurrently`.
- **What's wrong**: the docstring at `gates/__init__.py:3908` already admits it -- "Most gate jobs here are pure-Python, CPU-bound work ... sharing one `ThreadPoolExecutor`, so they all contend for the same GIL." archgate (91.5s) and sys (77s) are the two largest and both pure-Python; under threads they cannot run at the same time. Wall time for the gates stage is therefore ~sum (168.5s) not ~max (91.5s). The profile confirms the main thread blocked 466s on `_thread.lock.acquire`.
- **Failure scenario**: every run. The two giants serialize; a genuine parallel execution of just those two would save ~77s wall.
- **Fix direction**: run the CPU-bound gates (archgate, sys, dup, perf, pii, secrets) in a `ProcessPoolExecutor`, not threads. They already take plain-data inputs and return `tuple[Violation,...]` (picklable). The snapshot is the only large shared input -- build it once, pass it in. Bounded win: ~77s wall from overlapping the two giants alone; more once H1/H2 shrink each.

#### H4. No shared single-parse pass: the same file is read+tree-sitter-parsed 9-12x across one check
- **Where**: `src/frob/lang/__init__.py:156` `_parse` -- the sole read+parse chokepoint, **uncached** (no `lru_cache`, no per-run memo). Callers: `graph.build_graph` (1x, cached to sqlite), `arch` (2x, H1), `vet.scan_file_capabilities` (3x -- `_comment_byte_spans` `vet/_capability.py:184`, `_python_binding_capabilities` line 861, `_embedded_capabilities`/`_embedded_string_regions` line 302), `secrets_gate`, `pii_structural_gate`, `dup` (Rust), `sys` H2.
- **What's wrong**: every stage independently reads bytes and re-parses. `scan_file_capabilities` alone is 3 parses/file (measured), and inside `check_self_conformance` it is called **twice** per owned file (`strata/_selfconform.py:304` `_observed_extended_kinds_by_node` and line 332 `_observed_all_kinds_by_node`) = 6 parses/file for that path.
- **Failure scenario**: a 213-file source tree incurs ~2000-2500 tree-sitter parses per check when ~213 would suffice. tree-sitter parse + pure-Python walk is the dominant CPU cost of both giants.
- **Fix direction**: introduce a per-run parsed-tree cache keyed by (path, content-hash) at the `_parse` boundary -- a process-lifetime `dict[str, tuple[Tree,bytes,str]]` gated by a lock, or extend the existing `.frob/cache.db` to store trees (it already stores parse results for the graph). Fan one parse out to graph+arch+sys+vet+secrets. Bounded win: collapses the 2x/3x/6x multipliers; compounds with H1/H2.

#### H5. `scan_file_capabilities` is called twice per file in selfconform, doing identical parsing both times
- **Where**: `src/frob/strata/_selfconform.py:304` (`_observed_extended_kinds_by_node`) and `:332` (`_observed_all_kinds_by_node`) -- both loop `_sorted_owned_files(binding)` and call `scan_file_capabilities(path)` on the same files; the second only additionally applies `_KIND_MAP` normalization to the same result set.
- **What's wrong**: two full passes over the owned-file set, each re-reading + triple-parsing every file (H4), to compute two views of the same capability scan. The extended-kinds set is a subset of the all-kinds set.
- **Failure scenario**: on the `frob sys audit` / self-conformance path, owned-file count x 6 parses. Doubles the capability-scan cost of that path.
- **Fix direction**: scan each owned file once into `raw = scan_file_capabilities(path)`, then derive both `raw & _EXTENDED_KINDS` and the `_KIND_MAP`-normalized full set from that single result. One pass, one scan per file.

### MEDIUM

#### M6. `.hypothesis/` and `.serena/cache` are not skip-dirs -- 1342+ junk files walked/stat'd/read every stage
- **Where**: `src/frob/excludes.py:23` `BUILTIN_SKIP_DIRS` (missing `.hypothesis`, `.serena`); consumed by `arch/__init__.py:64`, `strata/_selfconform.py:234`/`421`, and every rglob-based stage.
- **What's wrong**: measured `_collect_files` keeps **1298 `.hypothesis/constants` + 44 `.hypothesis/examples` + `.serena/cache`** files. They have no tree-sitter grammar so they are not parsed, but each is stat'd, `read_bytes`'d (`arch/__init__.py:184`), `is_test_file`-checked, and grammar-probed -- 1342 wasted file opens per arch run, repeated in every other rglob stage.
- **Failure scenario**: any repo where hypothesis/serena have run (this one). Several seconds of pure I/O + iteration overhead across ~6 stages, scaling with the hypothesis DB size.
- **Fix direction**: add `.hypothesis`, `.serena` to `BUILTIN_SKIP_DIRS`. One-line fix, zero risk (neither is source).

#### M7. Every rglob stage descends the entire 745k-entry tree before filtering excludes
- **Where**: `arch/__init__.py:59` `for p in root.rglob("*")`; `strata/_selfconform.py:230` & `:421` (`root.rglob("*")` twice within one sys-audit run); `check/_python.py:679` `_has_bind_markers` (`rglob("*.py")`); `check/_python.py:131` `_build_import_graph`; `check/_python.py:770` `_run_exports` (`rglob("__init__.py")`).
- **What's wrong**: exclude globs (`.claude/worktrees/**`, which holds **45,091** of the repo's py files) are applied *after* `rglob` has already walked into and stat'd every excluded path. Measured: 6.1s per bare `rglob("*")`; `_collect_files` 9.1s. This walk is repeated independently by each stage (~6-8 walks/run = 40-70s of pure directory traversal).
- **Failure scenario**: this repo carries 45k worktree py files under <!-- frob:waive DOC006 reason="a runtime-varying directory of ephemeral session worktrees, never a single tracked path" -->`.claude/worktrees`; every stage walks all of them only to discard them.
- **Fix direction**: prune excluded/skip directories *during* traversal (os.walk with in-place `dirs[:]` filtering, or `os.scandir` recursion that does not descend a dir whose name is in `BUILTIN_SKIP_DIRS` or matches a directory-level exclude glob). Compute the file list once per run and share it across stages (tie to the snapshot from H4). Bounded win: turns ~7 full 745k walks into one pruned walk.

#### M8. `_has_bind_markers` reads bytes of every `*.py` in the tree (worktrees included) to decide whether to skip bind
- **Where**: `src/frob/check/_python.py:677` `_has_bind_markers` -- `for path in scan.rglob("*.py"): ... path.read_bytes()`, and it does **not** apply exclude globs.
- **What's wrong**: to answer "does any file contain `# BIND`", it may read all 45k+ worktree py files. It short-circuits on first hit, but a repo with no BIND markers (this one) reads every py file's full bytes.
- **Failure scenario**: no `# BIND` anywhere -> full read of ~45,700 py files just to return `None` from `_run_bind`. Silent because bind then reports nothing.
- **Fix direction**: honor exclude/skip dirs in the walk (M7), and grep via a cheap bounded read or reuse the shared parsed-file set (H4) rather than re-reading every file's full bytes.

#### M9. `build/lib` (a copied build artifact) is analyzed if present; skip-dir relies on name match that a nested layout can dodge
- **Where**: `src/frob/excludes.py:36` includes `"build"` in `BUILTIN_SKIP_DIRS`, applied per-path-component in `arch/__init__.py:64`. Present here: `build/lib` has 209 py files (a full copy of `src/frob`).
- **What's wrong**: the skip works for top-level `build/` (component "build" matches), so `build/lib` is correctly excluded in the current layout -- verified it did NOT appear in the 1991 kept files. **But** this is name-based, not path-based: any build output not literally named `build`/`dist`/`target` (e.g. `out/`, `_build/`, cmake `cmake-build-debug` -- the last is in `.gitignore` but not in `BUILTIN_SKIP_DIRS`) is fully analyzed, double-counting frob's own code and emitting duplicate arch/dup findings.
- **Failure scenario**: a project using `_build/` or `out/` for generated code gets every generated module parsed and arch-scanned, and `dup` flags generated-vs-source as clone groups.
- **Fix direction**: align `BUILTIN_SKIP_DIRS` with `.gitignore`'s build-artifact set (`cmake-build-*`, `out`, `_build`), or better, respect `.gitignore` directly for the walk.

#### M10. `_cached_snapshot` memoizes only the graph, and only for dup/arch *waiver* cross-reference -- not the arch/sys analysis itself
- **Where**: `src/frob/check/_python.py:231` `_cached_snapshot` (per-run `dict`, `_snapshot_cache`).
- **What's wrong**: the docstring claims it means the tree is not "re-walked a second/third time" -- true only for the *waiver edge* lookups in `_run_dup`/`_run_arch`. The actual `find_duplicates(scan)` (`_python.py:349`) and `analyze_project(root)` (`_python.py:440`) calls still do their own independent full walks and parses; the cached snapshot is used only to look up WAIVE edges afterward. So the memo saves one graph build for the advisory waiver join but does nothing for the 91.5s of arch parsing (H1).
- **Failure scenario**: reader assumes arch/dup reuse the cached parse; they do not. The 2x-parse cost in H1 persists despite this cache existing.
- **Fix direction**: extend the shared snapshot (or the H4 parsed-tree cache) to actually feed `analyze_project` and `find_duplicates`, not just their waiver post-pass.

### LOW

#### L11. DAEMON: the warm-graph incremental daemon (T-0177) is NOT built; `serve/` is a stateless FastMCP adapter
- **Where**: `src/frob/serve/` -- exposes read-only MCP tools only; `__main__.py:993` `_add_serve_parser` help = "MCP stdio adapter exposing frob's enforcement queries as tools".
- **What's wrong**: confirmed -- there is no long-lived process holding a warm graph across invocations. Each `frob check` cold-starts: it reloads the sqlite parse cache (which does give incremental parse reuse *for the graph*, hits=213/parsed=0 measured) but re-runs every walk and every arch/sys/vet parse from scratch. The only cross-invocation cache is `.frob/cache.db` for `build_graph` and coverage/baseline; arch/sys/vet trees are never persisted.
- **Failure scenario**: repeated `frob check` in a tight edit loop pays the full 745k walk + arch/sys parse every time even when one file changed.
- **Fix direction**: this is a genuinely large feature (a resident daemon). Smallest correct bounded step: persist arch/sys/vet per-file results in `.frob/cache.db` keyed by content-hash (the graph already does this), so an unchanged file skips re-analysis. That alone gives most of the incremental-daemon benefit without standing up a server.

#### L12. `_cached_snapshot` calls `build_graph` a second time even though `run_gates` already built it earlier in the same process
- **Where**: `src/frob/check/_python.py:245` `build_graph(scan, scan / _DUP_CACHE_REL)` vs `gates/__init__.py:3734` `build_graph(root, root / _CACHE_REL)`.
- **What's wrong**: within one `frob check`, `build_graph` is invoked at least twice (gates load + dup/arch waiver memo) against the same root. The sqlite cache makes the second cheap (0.3s warm, measured) but it is still a redundant call with its own sqlite open/query. `_CACHE_REL` and `_DUP_CACHE_REL` must also point at the same db or the second build is cold.
- **Failure scenario**: minor; ~0.3-2s and an extra sqlite connection. Real risk is cache-path divergence between the two constants causing a cold second build.
- **Fix direction**: build the snapshot once at the top of `run_check` and thread it into both the gates stage and the dup/arch stages.

---

## (E) META-GAP: why frob's own PERF gate (PERF001-004) missed all of this

- **Where**: `src/frob/perf/_rules.py` -- PERF001 (membership-in-loop), PERF002 (`.index/.count` in loop), PERF003 (nested-loop equality join), PERF004 (sort-in-loop). All are **per-function, single-token-stream lexical smells** (`_rules.py:1` "lexical, one-token-stream-deep linear-scan smells").
- **The blind class**: PERF001-004 reason about one function's token stream in isolation. The dominant cost here is **cross-stage recomputation of the same expensive input** -- "the same file is parsed N times across archgate/sys/vet", "the 745k-entry tree is walked 7 times", "build_graph's result is not reused by arch/sys". None of that is visible in any single function's tokens; it is an *inter-procedural, cross-module, algorithmic-complexity* property (the same pure input flows into an expensive pure function from multiple call sites without memoization).
- **What would catch it**: a **PERF005-class architectural check** operating on the call graph (frob already builds one -- T-0288 callgraph+inlining) rather than token streams. Concretely: flag when a pure, expensive function (a parse/walk over a whole-repo input -- `_parse`, `rglob`, `analyze_project`, `scan_file_capabilities`) is invoked from >1 stage within one command entry point without an intervening cache/memo boundary. This is "same expensive input recomputed N times across stages" as a graph reachability query: N distinct callers -> one hot pure sink -> no shared cache node between them.
- **This becomes its own remediation ticket** (companion to the already-filed T-0410): a cross-stage recomputation gate that fails when a repo-scale pure computation (walk/parse/hash over the file set) has >1 uncached call site reachable from a single command.

---

## Notes -- what I checked and found correct / what I skipped

**Verified correct (do not re-investigate):**
- **`build_graph`'s sqlite parse cache works**: measured 0 `_parse` calls / 213 hits / 0.3s on a warm `.frob/cache.db`. Incremental-by-content-hash for the graph specifically. The gap is that *only the graph* uses it (H4/M10).
- **Gate timing is honest CPU time** (T-0232 `_timed_job` uses `time.thread_time()`); the summary line is trustworthy per-gate attribution even though cProfile itself only sampled the main thread.
- **This checkout is on ext4 (`/dev/sdd`), not `/mnt/c`** -- the grounding's 13-60x WSL mount-tax confound (T-0245) does **not** apply to these measurements. The cost is CPU-bound parsing/walking, not mount I/O. (If the user's real runs are on a `/mnt/c` checkout, add that tax on top; but the redundancy findings are filesystem-independent.)
- **`build/lib` is currently excluded** by the `"build"` skip-dir (confirmed absent from the 1991 kept files); M9 is about the name-based fragility, not a live miss here.
- **`sys_gate` correctly no-ops** when there is no `design/` dir (`gates/__init__.py:2995`); the 77s is real work in a repo that has one.

**Skipped / skimmed (audit boundary):**
- Did not profile the C/C++/Rust/TS check paths (`run_check_cpp/rust/ts`) -- this repo is Python; those stages did not run.
- Did not micro-profile inside `check_import_conformance`/`bind_code` (H2) to split walk-vs-parse -- attributed the 77s to the stage via the timing line and the code path; a follow-up should confirm the walk/parse split there.
- cProfile's per-function `tottime` for the worker-thread gate bodies is unavailable (threads not sampled); if a finer function-level breakdown of *within* archgate is needed, re-run with `yappi` (thread-aware) or wrap each arch sub-check in its own `thread_time`.
- Did not audit the coverage/baseline/prework caches for correctness beyond confirming they are the only other cross-invocation caches; they measured <0.1s so are not a perf concern.
- Numbers are single-run (cProfile-inflated wall, real thread-time CPU). Ordering of the two giants is stable and large; exact seconds will vary run-to-run and shrink off cProfile.
