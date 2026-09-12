---
id: T-4449
title: 'Windows runner: platform_skipped empty in the self-gate AFTER the Test step
  (56 COV003 + 2 TEST002 persist past T-4447)'
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
- tests/test_testing_collect.py
- tests/test_testing.py
- tests/gates_suite/test_coverage.py
- tests/gates_suite/test_test_gate.py
- tests/unit/test_collect_python_cache*.py
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
CI run 34708801531 (head 59c43cb12, 2026-09-12, INCLUDES T-4447 7a84c576a, T-4429, T-4408), Windows self-gate: STILL 56 COV003 errors on tests/unit/test_conftest_stackdump.py (50) and tests/unit/test_stackdump.py (6) plus 2 TEST002 errors on src/frob/testing/_stackdump.py -- and the message is the GENERIC one ("does not resolve to a collected test; the collection cache is keyed on test file content..."), NOT the platform-skip WARN verdict text. So on the GitHub runner the platform-skip attribution never fires at all: CollectedTests.platform_skipped is EMPTY there, whereas on the winrun mirror (T-4444 and T-4447 agents, cold AND warm frob check) it is the correct 2-tuple and T-4447's pinning yields 0 errors. The ONLY sequencing difference is that on the runner the self-gate runs AFTER the full Test step (13933 tests) in the same checkout, so the Test step's side effects are what the check reads: the python collection cache (src/frob/testing/_collect_python_cache.py, keyed on test file content) written by tests that call collect_python_tests/_collect_python_cache against the real repo (tests/test_testing_collect.py, tests/test_testing.py, tests/gates_suite/test_coverage.py, tests/gates_suite/test_test_gate.py, tests/integration/test_interfaces.py, ...), or a .frob/ artifact (self-scan-cache, coverage-file-cache.json, gate-cache.db) left by the suite. INVESTIGATE ON THE MIRROR IN CI ORDER: (1) cold `frob check --only coverage --only test --json` -> record COV003/TEST002 error count for the two modules (expect 0 after T-4447); (2) run ONLY the test files above on the mirror (`.venv/Scripts/python.exe -m pytest <files> -q -p no:randomly`), then re-run the check -> if the 56 come back, bisect by file then by test to the one that poisons the cache/state and name it; (3) if that subset does not reproduce, run the full suite on the mirror (2h; run it detached and poll) and re-check. FIX: the poisoned artifact must not be readable as authoritative by the self-gate (e.g. the cache entry must carry platform_skipped, or the test must write to an isolated .frob/ via tmp_path, or the check must invalidate entries not keyed to this platform). ACCEPTANCE: (1) the runner-order reproduction on the mirror is recorded with the exact poisoning test named; (2) after the fix, the same sequence yields 0 COV003/TEST002 errors for the two modules; (3) CI Windows self-gate COV/TEST rows clean on the next push. Sprint v0.531.0 (CI green blocker). Supersedes the T-4444 hypothesis; complements T-4447 (which is correct but never reached on the runner).
