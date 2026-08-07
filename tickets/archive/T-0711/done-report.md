## Done report

## Done report

Changed:
src/frob/stats/_sketch.py::QuantileSketch
src/frob/stats/_sketch.py::DEFAULT_ALPHA
src/frob/stats/_sketch.py::new_sketch
src/frob/stats/_sketch.py::add_value
src/frob/stats/_sketch.py::merge_sketches
src/frob/stats/_sketch.py::decay_sketch
src/frob/stats/_sketch.py::total_weight
src/frob/stats/_sketch.py::quantile
src/frob/stats/_sketch.py::sketch_size_bytes
src/frob/perf/_sketch_store.py::SketchStoreConfig
src/frob/perf/_sketch_store.py::load_sketch_config
src/frob/perf/_sketch_store.py::stable_section_key
src/frob/perf/_sketch_store.py::get_sketch
src/frob/perf/_sketch_store.py::put_sketch
src/frob/perf/_sketch_store.py::store_size_bytes
src/frob/perf/_sketch_store.py::new_run_sketch
src/frob/perf/_models.py::PerfError.SketchStoreCorrupt (new ErrorSet member)
src/frob/perf/__init__.py (re-exports)
src/frob/stats/__init__.py (re-exports)
docs/modules/perf.md (new "Hot-graph sketch store (T-0711, EPIC T-0709)" section + Public API frob:describes entries + module listing)

Evidence (observed via `uv run pytest tests/unit/perf/test_sketch_store.py -v -n0`, 24 passed):
tests/unit/perf/test_sketch_store.py::TestQuantileSketchAlgebra::test_bimodal_quantiles_within_relative_error_and_under_1kb (bound to acceptance[0])
tests/unit/perf/test_sketch_store.py::TestQuantileSketchAlgebra::test_merge_is_associative (bound to acceptance[0])
tests/unit/perf/test_sketch_store.py::TestSketchStore::test_decayed_merge_converges_toward_recent_run_distribution (bound to acceptance[0])
tests/unit/perf/test_sketch_store.py::TestSketchStore::test_store_cap_evicts_coldest_section_first (bound to acceptance[0])
plus 20 more passing tests in the same file (algebra edge cases, config parsing, connection reuse, stable-key drift/digest behavior) -- see `frob:tests` directives on each public symbol for the exact binding.
tests/unit/perf/test_hotgraph.py: 8/9 passed in the same run; TestStackSampler::test_overhead_under_five_percent failed under `-n0` but passed cleanly on an isolated re-run -- pre-existing timing flake in T-0710's own sampler test (not touched by this ticket, no `_sampler.py`/`_hotgraph.py` code changed), reproduced flaky both before and after my change.

Filed: T-0883 (bug, scope tickets.md) -- `frob check --only gates-fast` surfaced TICK006 (T-0738's Done report cited a land-lost draft, since refiled as T-0877) after merging main forward; unrelated to T-0711's scope, filed rather than fixed silently.

Gates:
`uv run frob check --only lint --ticket T-0711`: PASS, 0 errors 0 warnings.
`uv run frob check --only gates-fast --ticket T-0711`: gate:COV/DEPR/DOC/DRIFT/FMT/INV/LANG/PLACE/REF/REG/REL/TEST/WAIVE/WALK all PASS 0 errors; gate:TICK FAILs with 1 pre-existing TICK006 error (T-0738, unrelated -- see Filed above) plus a pre-existing TICK003 archive-threshold warning.
`uv run frob check --only static --ticket T-0711`: PASS (frob-cycle/frob-dup/frob-arch/frob-exports all pass; remaining "N public symbols missing from __init__.py" notes on other packages are pre-existing, none in my touched files).
`uv run frob check --only gates-native --ticket T-0711`: PASS, 0 errors.
`uv run frob check --only gates-security --ticket T-0711`: PASS, 0 errors.
`git diff main --diff-filter=D --stat` after a second `git merge main` (main had advanced from 64d4d89a to 37ea6357 mid-ticket): empty -- no out-of-scope deletions.

Honest cuts / scope notes:
- `stable_section_key`'s line-drift-tolerant keying is layered so a REAL symbol digest (`frob.graph.digest.compute_digests`) can be wired in by a future ticket without touching this module's schema/merge/decay/eviction logic; today it falls back to `section.file` (qualname/kind-precise, not yet line-drift tolerant) since wiring the graph-digest lookup through the hot-graph resolver is outside this ticket's declared scope (`src/frob/stats/**`, `src/frob/perf/**`, `tests/unit/perf/`, `docs/modules/perf.md` -- not `src/frob/graph/**`). `Section.id`'s own T-0710 docstring names this exact ticket as the layer responsible for that keying, and `stable_section_key`'s docstring/tests document the current fallback explicitly rather than silently pretending it is already line-drift tolerant.
- No CLI subcommand or `frob test` integration wires a live `resolve_stream` output into `put_sketch` yet -- per T-0710's own perf.md doc, that live-invocation wiring is T-0711/T-0712's job and this ticket's own plan frames T-0712 as the consumer; this ticket ships the sketch algebra + persisted store T-0712 calls into, documented explicitly under "What this ticket did not wire" in docs/modules/perf.md's new section.
- `[perf.sketch]` frob.toml table is parsed/validated (`load_sketch_config`) but nothing in this ticket's scope reads it into a live collector run -- same T-0712 boundary as above.

### Changed
```
 docs/modules/perf.md                 | 106 +++++++++++
 src/frob/perf/__init__.py            |  16 ++
 src/frob/perf/_models.py             |   4 +
 src/frob/perf/_sketch_store.py       | 314 ++++++++++++++++++++++++++++++++
 src/frob/stats/__init__.py           |  18 ++
 src/frob/stats/_sketch.py            | 244 +++++++++++++++++++++++++
 tests/unit/perf/test_sketch_store.py | 335 +++++++++++++++++++++++++++++++++++
 tickets.md                           |  13 +-
 8 files changed, 1049 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/perf/test_sketch_store.py::TestQuantileSketchAlgebra::test_bimodal_quantiles_within_relative_error_and_under_1kb` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_sketch_store.py::TestQuantileSketchAlgebra::test_merge_is_associative` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_sketch_store.py::TestSketchStore::test_decayed_merge_converges_toward_recent_run_distribution` (pytest node id, verified passing when recorded)
- `tests/unit/perf/test_sketch_store.py::TestSketchStore::test_store_cap_evicts_coldest_section_first` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 1 error(s), 1043 warning(s), 220 waived
- error-findings: TICK006@tickets.md
