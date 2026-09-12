---
id: T-4447
title: 'Severity override re-promotes platform-skip WARN verdicts to ERROR: Windows
  COV003 x56 and TEST002 x2 persist'
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
- src/frob/gates/_waive.py
- tests/gates_suite/test_waive*.py
- tests/gates_suite/test_severity_overrides*.py
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
MEASURED on the Windows mirror by the T-4444 agent (2026-09-12, ticket failed there as wrong-premise): collect_python_tests / CollectedTests.platform_skipped is correct cold AND warm (platform_skipped=2 both ways), and the COV003/TEST002 detectors DO emit the deliberate platform-skip verdict at Severity.WARN (message text literally says "is platform-unavailable ... this is a WARN, not an error"). The error comes later: frob.gates._waive._apply_severity_overrides reads frob.toml [gates.severity] (COV003=error, TEST002=error) and re-severities EVERY violation of that rule to ERROR, exempting only Severity.UNRESOLVED -- so the platform-skip WARN verdict is silently promoted back to ERROR (JSON severity reads "error" while the message says WARN). This is why CI run 34675057655 (head d0fc8ba1e, which includes T-4382/T-4390/T-4408/T-4429) still shows 56 COV003 + 2 TEST002 errors on tests/unit/test_conftest_stackdump.py and tests/unit/test_stackdump.py on the Windows self-gate, while ubuntu/macOS are unaffected (nothing is platform-skipped there). ACCEPTANCE: (1) a detector-downgraded verdict carries an explicit marker (e.g. a `downgraded`/`verdict` field or a Severity.WARN_PINNED) that _apply_severity_overrides never promotes; (2) a unit test feeds a platform-skip WARN COV003 finding through _apply_severity_overrides with COV003=error configured and asserts it stays WARN; (3) measured on the mirror: `frob check --only coverage` (and the test gate) reports 0 COV003/TEST002 ERRORS for the two stackdump modules; (4) CI Windows self-gate COV/TEST rows clean on the next push. Sprint v0.531.0 (CI green blocker). Supersedes T-4444 (failed: wrong premise).
