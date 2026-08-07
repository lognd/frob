---
id: T-1445
title: Extend gate-result cache to root-scanning process-pool gates + add --no-cache
  CLI flag
state: done
kind: feature
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/check/**
- src/frob/_cli_parsers/_check.py
- src/frob/app/config.py
- src/frob/app/check_runner.py
- docs/modules/gates.md
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
- src/frob/gates/_gate_cache.py
- tests/test_gate_cache.py
- tests/_cache_transparency.py
- src/frob/app/_config_external.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'WAVE14-B (T-draft-57d64be9) TICK009 narrowing pass: replaced chronic-broad/over-threshold
    globs with the specific modules/docs/tests this ticket''s own plan names; expand
    with ''frob ticket scope --add'' as real work reveals more files.'
  actor: logan
  at: '2026-08-03'
- op: add
  glob: src/frob/gates/_gate_cache.py
  reason: 'Ticket''s own description says "Build on the existing gate-cache.db

    machinery" for extending caching to root-scanning process-pool gates.

    The new content-hash-keyed cache primitive for process-pool gates

    belongs in src/frob/gates/_gate_cache.py (the single existing home for

    this cache mechanism, T-0602), not duplicated inside __init__.py.

    tests/test_gate_cache.py and tests/_cache_transparency.py need matching

    coverage per the ticket''s own acceptance note ("extend those tests to

    the newly cached gates; parameterize the INV-050 harness").

    '
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/test_gate_cache.py
  reason: 'Ticket''s own description says "Build on the existing gate-cache.db

    machinery" for extending caching to root-scanning process-pool gates.

    The new content-hash-keyed cache primitive for process-pool gates

    belongs in src/frob/gates/_gate_cache.py (the single existing home for

    this cache mechanism, T-0602), not duplicated inside __init__.py.

    tests/test_gate_cache.py and tests/_cache_transparency.py need matching

    coverage per the ticket''s own acceptance note ("extend those tests to

    the newly cached gates; parameterize the INV-050 harness").

    '
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/_cache_transparency.py
  reason: 'Ticket''s own description says "Build on the existing gate-cache.db

    machinery" for extending caching to root-scanning process-pool gates.

    The new content-hash-keyed cache primitive for process-pool gates

    belongs in src/frob/gates/_gate_cache.py (the single existing home for

    this cache mechanism, T-0602), not duplicated inside __init__.py.

    tests/test_gate_cache.py and tests/_cache_transparency.py need matching

    coverage per the ticket''s own acceptance note ("extend those tests to

    the newly cached gates; parameterize the INV-050 harness").

    '
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/app/_config_external.py
  reason: 'WIRE001 (gate:WIRE) confirmed the new --no-cache CLI flag''s argparse dest

    (check_no_cache) is silently dropped by AppConfig.from_external because

    src/frob/app/_config_external.py''s field-name passthrough tuple does not

    list it -- the same T-1422 shape the gate error message names. Fixing

    this one-line field-name addition is required for --no-cache to actually

    work end-to-end (it is otherwise a dead flag), so it belongs in this

    ticket''s own scope, not a follow-up.

    '
  actor: logan
  at: '2026-08-05'
evidence:
- tests/test_gate_cache.py::TestRootContentKey::test_stable_when_nothing_changes
- tests/test_gate_cache.py::TestRootContentKey::test_changes_on_tracked_file_edit
- tests/test_gate_cache.py::TestRootContentKey::test_none_outside_a_git_repo
- tests/test_gate_cache.py::TestRootGateCache::test_miss_then_hit_skips_second_call
- tests/test_gate_cache.py::TestRootGateCache::test_tree_edit_forces_miss
- tests/test_gate_cache.py::TestRootGateCache::test_extra_change_forces_miss
- tests/test_gate_cache.py::TestRootGateCache::test_none_key_never_hits_and_never_stores
- tests/test_gate_cache.py::TestSplitProcessCache::test_use_cache_false_returns_everything_as_misses
- tests/test_gate_cache.py::TestSplitProcessCache::test_hit_removes_gate_from_remaining
- tests/test_gate_cache.py::TestSplitProcessCache::test_miss_keeps_gate_pending
- tests/test_gate_cache.py::TestRunGatesUseCacheProcessGates::test_second_warm_run_serves_process_gate_from_cache
- tests/test_gate_cache.py::TestRunGatesUseCacheProcessGates::test_tracked_file_edit_forces_process_gate_recompute
- tests/test_gate_cache.py::TestColdDiffOracleProcessGates::test_cache_agrees_with_cold_across_random_edits
- tests/test_gate_cache.py::TestCacheTransparencyProcessGates::test_root_gate_cache_observationally_transparent
designated_repro_test: null
acceptance:
- text: GIVEN a frob check invocation after M of K analyzed files changed since the
    cached run WHEN root-scanning process-pool gates execute THEN per-file gate findings
    for the K-M unchanged files are served from the content-hash-keyed cache without
    re-analysis, and a whole-repo warm check with a small touched set completes in
    seconds not minutes (measured and recorded in the ticket's evidence)
  evidence:
  - tests/test_gate_cache.py::TestRootContentKey::test_stable_when_nothing_changes
  - tests/test_gate_cache.py::TestRootContentKey::test_changes_on_tracked_file_edit
  - tests/test_gate_cache.py::TestRootContentKey::test_none_outside_a_git_repo
  - tests/test_gate_cache.py::TestRootGateCache::test_miss_then_hit_skips_second_call
  - tests/test_gate_cache.py::TestRootGateCache::test_tree_edit_forces_miss
  - tests/test_gate_cache.py::TestRootGateCache::test_extra_change_forces_miss
  - tests/test_gate_cache.py::TestRootGateCache::test_none_key_never_hits_and_never_stores
  - tests/test_gate_cache.py::TestSplitProcessCache::test_use_cache_false_returns_everything_as_misses
  - tests/test_gate_cache.py::TestSplitProcessCache::test_hit_removes_gate_from_remaining
  - tests/test_gate_cache.py::TestSplitProcessCache::test_miss_keeps_gate_pending
  - tests/test_gate_cache.py::TestRunGatesUseCacheProcessGates::test_second_warm_run_serves_process_gate_from_cache
  - tests/test_gate_cache.py::TestRunGatesUseCacheProcessGates::test_tracked_file_edit_forces_process_gate_recompute
  - tests/test_gate_cache.py::TestColdDiffOracleProcessGates::test_cache_agrees_with_cold_across_random_edits
  - tests/test_gate_cache.py::TestCacheTransparencyProcessGates::test_root_gate_cache_observationally_transparent
threat: null
component: null
---
Found while working T-1346 (memoize gate results on content digests).

T-1346 wired the existing T-0602 per-gate result cache into the real
`frob check` CLI path (previously built but never actually engaged by any
`frob check` call site) and turned it on by default for the closed
`_CACHEABLE_GATES` allowlist (drift, test, policy, parse_failures, debt,
lang_conformance, affect_drift). Two things were deliberately left out of
that ticket's scope (src/frob/gates/**, src/frob/check/**,
docs/modules/gates.md) and are recorded here rather than folded in
silently:

1. A first-class `--no-cache` CLI flag. T-1346 shipped an environment-
   variable escape hatch (FROB_NO_GATE_CACHE=1) instead, because a real
   argparse flag needs `src/frob/_cli_parsers/_check.py`,
   `src/frob/app/config.py` (AppConfig.check_no_cache), and
   `src/frob/app/check_runner.py` (threading `no_cache=cfg.check_no_cache`
   into the four _dispatch_check_* functions) -- all outside T-1346's
   declared scope. The env var is a real, working escape hatch today; a
   CLI flag is a small, mechanical follow-up mirroring how `--delta` is
   already threaded through the exact same files.

2. The bigger lever: `_CACHEABLE_GATES` only covers thread-pool gates that
   read `st.snapshot` alone via TrackedSnapshot. The gates T-1346's own
   body measured as the dominant CPU cost of a full `frob check` -- sys
   (~31-39s), perf (~29-38s), arch (~24-29s), clones/dup (~19-22s),
   pii_structural (~12-14s), secrets, coverage, dead_symbols, deprecated,
   opaque -- all run as _ProcessJobs that take `st.root` directly (an
   unbounded filesystem walk TrackedSnapshot cannot observe), so none of
   them are eligible for the current cache design at all. This is where
   the actually large wall-clock win lives; T-1346 only wired the cheap
   thread-pool gates that were already technically cacheable.

Extending the cache to the root-scanning process-pool gates needs real
design work, not a mechanical extension of TrackedSnapshot: a
root-content-hash (or similar) invalidation key that can observe what a
root-scanning gate actually touched, a plan for the multi-process
dispatch shape (_ProcessJob results currently never pass through the
thread-pool-only `evaluate_cacheable_gate` path), and the same
correctness-over-speed posture T-0602/T-1346 both insisted on (never
serve a stale result silently). This is the natural continuation of the
T-1344 gate-speed leaf and should be scoped as its own ticket rather than
squeezed into T-1346's remainder.