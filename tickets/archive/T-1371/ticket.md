---
id: T-1371
title: 'Drain EXHAUST001/EXHAUST002 to zero: unresolvable escapes and undeclared KeyError/TypeError'
state: done
kind: bug
origin: human
created: '2026-08-01'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/**
- tests/test_gates.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_gates.py
  reason: T-1371's own prior wip session added TestParseLineElFallbacks pinning the
    fallback values of the widened _parse_line_el guards; the test file itself needs
    to be in scope for COV002 to recognize the diff as covered
  actor: logan
  at: '2026-08-02'
- op: add
  glob: design/frob.strata
  reason: design/frob.strata's testsuite interface list is mechanically synced (frob
    sys sync-interface) and drifted while this ticket's worktree was open; keeping
    the sync in scope avoids a SCOPE001 finding on generated-artifact drift unrelated
    to the drain itself
  actor: logan
  at: '2026-08-02'
evidence:
- tests/test_app_daemon_proxy.py::TestProbeDaemonVersion::test_matching_version_is_live
- tests/test_app_daemon_proxy.py::TestProbeDaemonVersion::test_different_version_is_skew_not_live
- tests/test_gates_fix_engine.py::TestSuppress001StringLiteralSafety::test_hash_suppression_inside_string_literal_is_not_a_comment
- tests/test_graph_lock.py::TestCacheLockRetry::test_retries_then_succeeds_past_a_transient_lock
- tests/test_graph_lock.py::TestCacheLockRetry::test_raises_cache_locked_once_budget_exhausted
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_hash_inside_string_literal_is_not_treated_as_comment
- tests/test_vet.py::TestScanTreeTimeout::test_slow_package_returns_within_timeout_not_task_duration
- tests/test_ticket_land.py::TestCoverageLockConflictMerges::test_conflicting_lock_merges_to_the_higher_of_both_sides
- tests/test_gates.py::TestWireGate::test_new_cli_dest_missing_from_config_external_is_flagged
- tests/test_gates.py::TestWireGate::test_new_cli_dest_present_in_config_external_is_not_flagged
- tests/test_gates.py::TestWireGate::test_new_kwonly_param_never_passed_is_flagged
- tests/test_gates.py::TestWireGate::test_new_kwonly_param_passed_at_call_site_is_not_flagged
designated_repro_test: null
acceptance:
- text: GIVEN main WHEN frob check --only gates runs THEN gate:EXHAUST reports 0 EXHAUST001
    and 0 EXHAUST002 warnings
  evidence:
  - tests/test_app_daemon_proxy.py::TestProbeDaemonVersion::test_matching_version_is_live
  - tests/test_app_daemon_proxy.py::TestProbeDaemonVersion::test_different_version_is_skew_not_live
  - tests/test_gates_fix_engine.py::TestSuppress001StringLiteralSafety::test_hash_suppression_inside_string_literal_is_not_a_comment
  - tests/test_graph_lock.py::TestCacheLockRetry::test_retries_then_succeeds_past_a_transient_lock
  - tests/test_graph_lock.py::TestCacheLockRetry::test_raises_cache_locked_once_budget_exhausted
  - tests/test_pii_structural_gate.py::TestKeywordSweep::test_hash_inside_string_literal_is_not_treated_as_comment
  - tests/test_vet.py::TestScanTreeTimeout::test_slow_package_returns_within_timeout_not_task_duration
  - tests/test_ticket_land.py::TestCoverageLockConflictMerges::test_conflicting_lock_merges_to_the_higher_of_both_sides
  - tests/test_gates.py::TestWireGate::test_new_cli_dest_missing_from_config_external_is_flagged
  - tests/test_gates.py::TestWireGate::test_new_cli_dest_present_in_config_external_is_not_flagged
  - tests/test_gates.py::TestWireGate::test_new_kwonly_param_never_passed_is_flagged
  - tests/test_gates.py::TestWireGate::test_new_kwonly_param_passed_at_call_site_is_not_flagged
threat: null
component: null
---
95 findings at drive start (62 EXHAUST001, 33 EXHAUST002). Each is either a real unhandled-exception path (fix the handling or add a catch-all) or a case for an explicit frob:raises declaration. Prefer declaring the truth over blanket except Exception where the escape is genuinely intended.