---
id: T-4444
title: 'Windows self-gate: platform_skipped lost on a warm collection cache, 56 COV003
  and 2 TEST002 persist after T-4429'
state: queued
kind: bug
origin: agent
created: '2026-09-12'
priority: critical
parent: T-3505
tier: ticket
sprint: v0.531.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_collect_python_cache.py
- src/frob/testing/_collect.py
- src/frob/testing/_collect_shared.py
- tests/unit/test_collect_python_cache*.py
- tests/gates_suite/test_coverage.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 34675057655 (head d0fc8ba1e, 2026-09-12, which INCLUDES T-4429 cddb38dfe and T-4408), Windows self-gate: still 56 COV003 errors (50 in tests/unit/test_conftest_stackdump.py, 6 in tests/unit/test_stackdump.py -- both modules skip at module level when sys.platform == "win32") and 2 TEST002 errors on src/frob/testing/_stackdump.py::dump_all_thread_stacks and ::install_stackdump_handler. Message: "does not resolve to a collected test; the collection cache is keyed on test file content and refreshes automatically". T-4429 measured _load_tests(root).platform_skipped correct on the winrun mirror, yet the runner does not attribute. HYPOTHESIS to verify first: the mirror was measured COLD (fresh pytest --collect-only), whereas on the runner the self-gate runs AFTER the Test step, so collect_python_tests served the CACHED collection (src/frob/testing/_collect_python_cache.py) -- and _last_platform_skipped there is a module global set only on a fresh collect (_set_collection_platform_skipped, T-4382), so a cache hit yields platform_skipped == () and every skipped module's evidence falls through to COV003/TEST002. Reproduce on the mirror by running the coverage and test gates TWICE (second run cache-warm) and diffing the COV003 count. ACCEPTANCE: (1) platform_skipped is persisted in the collection cache entry and restored on a hit; (2) a unit test feeds a warm cache and asserts platform_skipped survives; (3) measured on the mirror: cache-warm run has 0 COV003 for the two stackdump modules; (4) CI Windows self-gate COV/TEST rows clean on the next push. Sprint v0.531.0 (CI green blocker).
