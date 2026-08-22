---
id: T-2806
title: Stamp the parse-artifact cache env before build_graph, not just before the
  gate process pool
state: done
kind: feature
origin: human
created: '2026-08-21'
priority: high
parent: T-2790
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
- tests/unit/test_check.py
evidence_scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_check.py::TestParseArtifactCacheWarmedBeforeGraphBuild::test_env_var_set_before_load_inputs_builds_graph
- tests/unit/test_check.py::TestParseArtifactCacheWarmedBeforeGraphBuild::test_stamp_is_idempotent_across_both_call_sites
- tests/test_gates.py::test_gates_run_gates_integration
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: f51368e297bdcb913f819b1c34e034955331fed8
---
Found while working T-2797 (parent T-2790). T-2797 assumed frob.lang's
persistent parse-artifact cache (T-1464) only stores the raw tree-sitter
parse and not extract()'s structured output. That premise is FALSE for
current code: _parse_file_with_artifact_cache already persists the whole
ParsedFile (symbols/comments included) to .frob/parse-artifacts.db, and
tests/unit/test_lang_artifact_cache.py TestParseFileArtifactCache
test_hit_skips_extract already proves a hit skips extract() entirely.
T-2797 was failed as undoable-as-scoped because the actual remaining
redundancy lives outside its declared scope (src/frob/lang/__init__.py
only).

Measured in a real, unbudgeted "frob check --only <gate>" run on this
repo (FROB_NO_GATE_CACHE=1 to bypass the unrelated whole-run replay
cache), fleet LOAD ~9-14 (some contention, noted):
  - perf cold (empty parse-artifacts.db): 63.66s
  - dead_symbols cold (empty parse-artifacts.db): 42.69s
  - dead_symbols warm (cache pre-populated by the perf run above,
    covering ~1197 files): 27.25s -- a real ~36 percent cut, confirming
    the T-1464 mechanism already works when NOT racing.
  - perf + dead_symbols run together via --only perf --only dead_symbols
    from an EMPTY cache: perf=53.89s, dead_symbols=28.67s -- both still
    pay close to their cold cost, because they are dispatched into the
    SAME ProcessPoolExecutor wave (frob.gates._PROCESS_POOL_GATES) and
    race: neither's cache writes are reliably visible to the other by
    the time it reaches the same file.

Root cause of the remaining redundancy: _load_inputs (via
_load_graph_queue_lock -> frob.graph.build_graph) runs in the pool
OWNER process BEFORE _stamp_worker_parse_artifact_cache_env sets
FROB_PARSE_ARTIFACT_CACHE, which only happens later inside
_open_process_pool/_assemble_gate_report. build_graph's own
frob.lang.parse_file calls (which parse+extract every file to build
the symbol graph) therefore NEVER see the persistent cache and never
warm it -- the very first opportunity to populate .frob/parse-
artifacts.db for free, before any gate worker even starts, is skipped
today. Every extract-heavy ProcessPoolExecutor gate (perf, dead_symbols,
archgate, sys, clones) then independently pays a cold first-touch cost,
and any two of them dispatched into the same wave race each other for
it on top of that.

Plan (not implemented here): move _stamp_worker_parse_artifact_cache_env
(or an equivalent stamp) to run BEFORE _load_inputs/build_graph in
run_gates/_run_gates_bounded, so the owner process's own parse_file
calls during graph construction populate the shared disk cache --
every process-pool gate worker then starts from an already-warm cache
instead of racing to fill it. Needs: a before/after identical real
check finding-count run (same hard constraint T-2790's children all
carry), and a timing re-measurement of perf+dead_symbols run together
from a cold cache to confirm the race is actually closed (not just
individually-warm timings, which is what this ticket's own
measurements above already show working).