---
id: T-4669
title: 'SF-04/SF-20: digest-keyed cache for capability_via_site_counts and load_design_ids
  -- 17.8s warm per call, no memoization'
state: done
kind: feature
origin: agent
created: '2026-09-19'
priority: high
parent: T-4664
tier: ticket
sprint: v0.536.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_effects.py
- src/frob/strata/_design_load.py
- tests/unit/strata/test_strata_scan_cache.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/strata/test_strata_scan_cache.py::TestCapabilityViaSiteCountsCache::test_second_call_in_process_is_a_cache_hit_under_one_second
- tests/unit/strata/test_strata_scan_cache.py::TestCapabilityViaSiteCountsCache::test_changed_tracked_file_invalidates_the_cache
- tests/unit/strata/test_strata_scan_cache.py::TestLoadDesignIdsCache::test_second_call_in_process_is_a_cache_hit
- tests/unit/strata/test_strata_scan_cache.py::TestLoadDesignIdsCache::test_changed_design_file_invalidates_the_cache
designated_repro_test: null
acceptance:
- text: Given capability_via_site_counts measured 23.03s cold and 17.83s on a second
    call in the SAME process at HEAD c8f56ef10, when this lands, then a test calling
    it twice in one process asserts the second call completes in under 1 second --
    a positive control that fails today at 17.83s.
  evidence:
  - tests/unit/strata/test_strata_scan_cache.py::TestCapabilityViaSiteCountsCache::test_second_call_in_process_is_a_cache_hit_under_one_second
  - tests/unit/strata/test_strata_scan_cache.py::TestLoadDesignIdsCache::test_second_call_in_process_is_a_cache_hit
- text: Given the cache must never serve a stale scan as a clean one, when a tracked
    source file under src/ changes, then a test asserts the next lookup MISSES and
    rescans, and the lookup logs its digest and hit/miss at every call.
  evidence:
  - tests/unit/strata/test_strata_scan_cache.py::TestCapabilityViaSiteCountsCache::test_changed_tracked_file_invalidates_the_cache
  - tests/unit/strata/test_strata_scan_cache.py::TestLoadDesignIdsCache::test_changed_design_file_invalidates_the_cache
threat: null
component: strata
anchor: false
anchor_reason: null
land_commit: null
---
SF-04 (HIGH) + SF-20 (LOW). Leaf of story A (T-4664) under epic T-4662.
Story points: 3. IMMEDIATELY DISPATCHABLE -- no blockers.

EVIDENCE, measured in-process at HEAD c8f56ef10:

    load_design_ids(root, "design")           0.026s  (0.022s second call)
    capability_via_site_counts(model, root)  23.03s   (17.83s second call, SAME process)
    -> 71 keys, 1,634 total sites

There is no memoization anywhere: repeating the call in the same interpreter
costs 17.8s AGAIN. `capability_via_site_counts` (src/frob/strata/_effects.py:1154)
is the quantity SYS111, the land pre-commit check, the composed-tree check and
the detached post-land sweep each need, and
src/frob/gates/_fix_engine_sync.py:1313 takes TWO snapshots per call
(current_counts and before_counts), i.e. two full scans.

Container cost from telemetry: `check --json` n=145, median 717.1s, max 1684.5s;
`verify drain-async` n=64, median 1008.5s.

SF-20: `load_design_ids` (src/frob/strata/_design_load.py) has no lru_cache, no
mtime and no digest check. Planner-verified call sites, one re-parse each per
run: src/frob/app/sys_runner.py:319, :446, :824; src/frob/app/deploy_runner.py:84;
src/frob/app/ticket_runner/_land_cmd.py:900;
src/frob/gates/_policy_weakening_gate.py:172;
src/frob/gates/_fix_engine_sync.py:1187. At 0.022s each this is cheap on its own
-- it is filed here because it is the natural place to hang SF-04's cache, and
because it is WHY SF-11's warning appears ~12.7 times per land.

WHERE THE COST IS NOT: the audit measured parse+elaborate+merge of all of
design/ (26 nodes, 119 flows, 1 boundary, 36 claims) at 0.026s. strata-core's
semi-naive Datalog fixpoint is NOT the bottleneck at frob's own model size. The
18-23s is entirely the PYTHON-side per-file capability scan over src/ and
tests/, repeated per caller. Do not go optimising the kernel.

WHAT TO BUILD
A cache keyed on a content digest of the scanned tree (not mtime -- worktrees
and git checkouts rewrite mtimes), covering both capability_via_site_counts and
load_design_ids, valid within a process and across processes via a file under
.frob/. Per memory/silent-zero-is-the-dominant-bug-class.md, the cache must make
a stale hit impossible to mistake for a clean scan: log the digest and whether
the result was a hit at every lookup.

POSITIVE CONTROL (the test that fails today)
A test that calls capability_via_site_counts twice in one process against the
repo tree and asserts the second call completes in under 1 second. It fails at
HEAD today, measurably, at 17.83s. A second test must assert the cache MISSES
after a tracked source file changes (the positive control on the invalidation
path, per memory/positive-control-or-it-proves-nothing.md).