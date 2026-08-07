---
id: T-0846
title: 'land: ClaimDivergence compares exact error counts across run contexts; scoped-flaky
  rules make landing a refresh-retry loop'
state: done
kind: bug
origin: agent
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/**
- tests/test_ticket_land.py
- src/frob/app/ticket_runner.py
- tests/test_ticket_done_report_claims.py
- tests/unit/test_ticket_runner_gate_findings.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: adversarial regression test for the gate-error-count comparison fix lives
    here, mirroring _land.py's own module
  actor: logan
  at: '2026-07-23'
- op: add
  glob: src/frob/app/ticket_runner.py
  reason: 'reviewer-directed rework (reject #1): identity-based ClaimDivergence comparison
    needs the real check_gate_findings closure wired here, alongside the existing
    _check_gates_summary_fn it shares a subprocess run with'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_ticket_done_report_claims.py
  reason: 'reviewer-directed rework (reject #1): DoneReportClaims gained error_findings;
    adding round-trip coverage in its existing dedicated test module'
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/test_ticket_runner_gate_findings.py
  reason: 'TEST016 round: dedicated unit tests for _check_gate_findings_fn''s subprocess-kwarg
    shape and parse-boundary logic, mocking the guarded_subprocess_run seam per the
    test_ticket_runner_land_release.py precedent'
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_lower_gate_error_count_than_claim_still_lands
- tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_masked_self_introduced_error_in_own_scope_still_refuses_via_identity
- tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_error_findings_round_trips_through_a_done_report_body
- tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_measured_empty_error_findings_differs_from_none
- tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn::test_parses_multiple_findings_from_errors_section
- tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn::test_refused_spawn_returns_none_not_empty_set
- tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn::test_unparsable_output_returns_none
- tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn::test_no_errors_heading_with_parsable_summary_is_measured_empty
- tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn::test_spawn_kwargs_capture_output_text_and_no_check
- tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree::test_uses_tree_venv_python_when_present
- tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree::test_falls_back_to_sys_executable_when_no_tree_venv
- tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree::test_check_gate_findings_fn_spawns_the_tree_venv_python
- tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree::test_check_gates_summary_fn_spawns_the_tree_venv_python
designated_repro_test: null
threat: null
component: null
---
T-0754's claim check compares the captured error COUNT against a fresh post-merge count. Three failure modes burned 5 land attempts this session (T-0755/T-0640): (1) WAIVE004 self-declares 'known-flaky for diff-scoped rules... trust this only from a full, unscoped run' yet still counts toward the scoped-run error total the claim check compares; (2) the capture is taken at done-report time in a different tree state than land's post-merge check, so any main-side drift (even fixes) diverges the count; (3) the remedy loop (refresh done-report, commit, retry land) is manual and non-obvious. Fix direction: compare a SET of finding identities (rule id + location) not a count, exclude rules that self-declare scoped-run flakiness from the comparison, and/or have land re-capture the claim itself post-merge instead of refusing.