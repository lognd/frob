---
id: T-4390
title: COV003 platform-skip attribution lost on a warm collection cache
state: done
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_collect.py
- src/frob/testing/_collect_shared.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_testing_collect.py::TestPlatformSkippedSurvivesCacheHit::test_platform_skipped_round_trips_through_a_cache_hit
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Coordinator measurement, Windows CI run 34415921529 (head 7ad69b30f, includes T-4382): the Windows self-gate still reports gate:COV 56 errors, dominated by COV003, on the SAME platform-skipped evidence (tests/unit/test_stackdump.py etc) T-4382's fix targets -- so T-4382's platform_skipped attribution did not take effect on that runner. Root cause: collect_python_tests's own code comment already documents this as a known, unfixed gap -- a pytest-collection cache HIT returns early without ever calling _run_collect_only, so _platform_skipped_test_modules() reads back () even when the ORIGINAL (cache-miss) collection found platform-skipped modules, because the plain node-id cache (.frob/pytest-collect.json) never stored skip reasons at all. On CI, the Windows job's own TEST step runs frob test BEFORE the self-gate frob check step within the same checkout, so the self-gate's own internal collection call hits a cache already warmed by that earlier step -- exactly this gap, live. Fix: extend the shared node-id cache (_load_cache/_store_cache in _collect_shared.py, used by rust/ts/ctest/kotlin too, so this must be additive-only for those) with an optional extra JSON payload a collector can round-trip through a cache hit; have collect_python_tests store/restore platform_skipped through it.