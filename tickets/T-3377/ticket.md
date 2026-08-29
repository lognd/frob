---
id: T-3377
title: Fresh worktree with no built natives produces ~20 false gate-test failures
state: queued
kind: docs
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/audits
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
MEASURED today (Series EF, re-measuring chunk3a/3b/3c): a raw git worktree created via 'git worktree add' + 'uv run pytest' has NO native extensions built (strata_core/frob_core not importable) until 'frob natives build' (or 'make core') runs. Before that, tests/test_gates.py's TestSysGate/TestSelfAuditGate/TestKnownGateRuleIds class (~20 tests) fail with e.g. 'assert 0 == 1' on SYS001/SYS002/SYS004/DOC003/SELFAUDIT001 checks, because sys_gate's strata design-model parsing silently degrades (NativeExtensionUnavailable, T-0133) when the native isn't present -- the test synthesizes a design/m.strata file expecting a real dangling-channel violation, but with no native the design file simply fails to parse and the gate suppresses its own findings ('SYS001: suppressed, 1 design file(s) failed to load'). This produced a false ~20-failure spike that looked exactly like a real regression on first measurement; confirmed by re-running the identical failing test after 'frob natives build' (clean pass). This has already cost multiple agents today (per the coordinator) re-discovering the same trap. Ask: either (a) make 'frob natives build' an automatic step the FIRST 'uv run pytest'/'uv run frob check' in a freshly-created worktree performs (a natives-staleness check already exists per src/frob/strata/_native_staleness.py -- extend it to also fire on total absence, not just staleness, with an actionable error instead of a silent pure-python degrade for THIS specific repo-self-test class), or (b) document this loudly in the worktree-setup path (Makefile 'core:' target, docs/, and/or a one-line startup banner) so agents building a raw worktree see it before running tests, not after debugging a false failure spike. Filed as docs-kind since the minimum fix is documentation; a code-kind follow-up (loud native-absence error in the specific self-test gate path) may be warranted after triage.