---
id: T-1529
title: extend cache-transparency harness to coverage-lock/hotgraph-sketch/check-budget-timing
  caches
state: done
kind: invariant
origin: human
created: '2026-08-04'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_cache_transparency.py
- invariants/INV-050.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_cache_transparency.py::TestCoverageLockCacheTransparency::test_cold_warm_agree_across_random_edits
- tests/test_cache_transparency.py::TestHotgraphSketchCacheTransparency::test_cold_warm_agree_across_random_edits
- tests/test_cache_transparency.py::TestBudgetTimingCacheTransparency::test_cold_warm_agree_across_random_edits
designated_repro_test: null
threat: null
component: null
---
Filed while working T-1519 (cache observational-transparency invariant INV-050). Three caches were
deliberately left out of the cold==warm property harness because they are not correctness-critical
(they never change a gate's PASS/FAIL result or violation fingerprint, only advisory precision or
scheduling), but a full arbitrary-edit-sequence sweep against them is still worth having for
completeness:

- .frob/coverage-stamp + frob-coverage.lock.json (src/frob/gates/_coverage.py) -- already has
  dedicated provenance/ratchet regression tests (T-1435/T-1406/T-1363) but no generic cold/warm
  fingerprint sweep of the kind INV-050's harness provides for other caches.
- .frob/hotgraph_sketches.db (src/frob/perf/_sketch_store.py) -- perf advisory sketch store.
- .frob/check-budget-timing.json (src/frob/app/_check_chunking.py) -- --budget group-selection
  scheduling heuristic.

See invariants/INV-050.md's inventory table for the full reasoning per cache.