---
id: T-1578
title: Natives-stale worktree gate runs must signal degradation structurally, not
  report zero findings
state: done
kind: bug
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/perf/**
- src/frob/gates/**
- src/frob/app/ticket_runner/_land_cmd.py
- docs/modules/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestPerfReachDegradedMarker::test_no_stale_natives_returns_none
- tests/test_gates.py::TestPerfReachDegradedMarker::test_stale_frob_core_returns_the_marker
- tests/test_gates.py::TestPerfReachDegradedMarker::test_stale_unrelated_native_returns_none
- tests/test_ticket_work_and_land_finish.py::TestWorktreeNativesVerifiablyHealthy::test_healthy_natives_return_true
- tests/test_ticket_work_and_land_finish.py::TestWorktreeNativesVerifiablyHealthy::test_stale_after_autorebuild_attempt_returns_false
- tests/test_ticket_work_and_land_finish.py::TestWorktreeNativesVerifiablyHealthy::test_unimportable_native_returns_false
designated_repro_test: null
threat: null
component: null
---
Every land's pre-land Tier-A pass runs fix_waive004_stale_waiver's self-manufactured run_gates() inside the WORKTREE, where native builds (frob_core/strata_core) are routinely stale/missing. The perf/reach substrate then silently under-reports to ZERO findings, all 73 PERF004 (+PERF001/2/3/8) waivers read stale, and only the T-1323 mass-invalidation COUNT heuristic saves the waivers -- _degraded_verification_reason's structural natives check does NOT fire, which is the gap: the run looks healthy while its analysis layer is dead.

Fix, two layers: (1) the perf/reach substrate must emit a structural degraded-run signal (skipped-stage / import-failure marker on the report) when its native deps fail to import or are content-stale, so _degraded_verification_reason catches it BEFORE the count heuristic -- 'zero findings' and 'could not analyze' must be distinguishable everywhere, not just for perf; (2) the pre-land Tier-A pass in _land_cmd.py should preflight-check worktree natives and skip the WAIVE004 self-run entirely when stale -- today it burns a full run_gates() per land whose verdict is guaranteed untrustworthy, then logs a scary ERROR. Expected effect: the per-land 'WAIVE004 auto-fix: 73 directives went stale' ERROR disappears and each land gets a full gates-run cheaper.