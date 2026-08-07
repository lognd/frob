---
id: T-0754
title: 'captured Done-report claims: test-count and gate-state fields populated from
  real command output, re-verified at land'
state: done
kind: security
origin: human
created: '2026-07-22'
priority: high
parent: T-0417
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/app/ticket_runner.py
- docs/modules/tickets.md
- tests/test_ticket_land.py
- tests/test_ticket_done_report_claims.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: T-0754 needs done-report/land capture+reverification tests
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/test_ticket_done_report_claims.py
  reason: T-0754 needs done-report/land capture+reverification tests
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_round_trips_through_a_done_report_body
- tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_missing_section_returns_none
- tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_claims_omitted_when_no_callables_supplied
- tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_claims_captured_from_real_callables
- tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_divergent_real_count_is_recorded_not_the_typed_narrative
- tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_gate_state_only_no_test_capture_leaves_claims_out
- tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_matching_claims_land_succeeds
- tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_test_count_refuses_land
- tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_gate_errors_refuses_land
- tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_no_claims_section_skips_reverification
- tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_free_prose_elsewhere_never_masquerades_as_claims
- tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_only_lines_inside_the_claims_heading_count
- tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_gate_errors_refuses_land
- tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_warning_or_waived_count_alone_still_lands
- tests/test_ticket_land.py::TestDoneReportThenLandRealClosuresEndToEnd::test_real_closures_done_report_then_land_succeeds
designated_repro_test: null
acceptance:
- text: GIVEN a done-report whose typed test count differs from the actual evidence
    run WHEN done-report captures THEN it records the real count and flags the divergence;
    GIVEN a captured gate-state that no longer holds at land THEN land errors
  evidence:
  - tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_round_trips_through_a_done_report_body
  - tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_missing_section_returns_none
  - tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_claims_omitted_when_no_callables_supplied
  - tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_claims_captured_from_real_callables
  - tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_divergent_real_count_is_recorded_not_the_typed_narrative
  - tests/test_ticket_done_report_claims.py::TestSetDoneReportClaims::test_gate_state_only_no_test_capture_leaves_claims_out
  - tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_matching_claims_land_succeeds
  - tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_test_count_refuses_land
  - tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_gate_errors_refuses_land
  - tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_no_claims_section_skips_reverification
  - tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_free_prose_elsewhere_never_masquerades_as_claims
  - tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_only_lines_inside_the_claims_heading_count
  - tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_gate_errors_refuses_land
  - tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_divergent_warning_or_waived_count_alone_still_lands
  - tests/test_ticket_land.py::TestDoneReportThenLandRealClosuresEndToEnd::test_real_closures_done_report_then_land_succeeds
threat: null
component: null
---
Root-cause analysis 2026-07-22: across ~15 review rejects this session, the single largest class was the Done report claiming numbers/state that did not reproduce (T-0572 142-reported-as-145 and 0-errors-that-was-27; T-0710/T-0724 undisclosed gate state; the phantom-filing family already closed by TICK006). The Done report is the ONLY pipeline artifact that is unverified free prose -- evidence ids resolve, scope binds, the diff is real, but the prose claims are typed from memory/stale runs. Fix: CAPTURE, do not type. Extend frob ticket done-report so structured claim fields are populated from REAL command output, not narrative: (1) a test-result field captured by actually running the recorded evidence node ids (pass count + a digest of the run), refusing to record a count the run did not produce; (2) a gate-state field auto-filled from a fresh frob check --ticket capture (the "clean except X" line becomes generated, never typed); (3) at land, re-verify the captured claims still hold against the merged tree and ERROR on divergence. The narrative prose stays for WHY; the CHECKABLE claims become captured artifacts. This is the general form of TICK006 (which made filing-claims checkable) applied to test-count and gate-state claims.