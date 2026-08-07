---
id: T-0850
title: 'land: gate-state ClaimDivergence still vulnerable to WAIVE004 scoped-run flakiness
  (needs finding-identity comparison)'
state: done
kind: bug
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/check.py
- src/frob/app/ticket_runner.py
- src/frob/tickets/_land.py
- docs/modules/gates.md
- tests/unit/test_ticket_runner_gate_findings.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: 'Doc anchor for the new SCOPED_RUN_FLAKY_RULE_IDS public constant belongs
    in docs/modules/gates.md''s existing Public API section (COV001-doc-anchor requirement);
    the ticket''s original scope only listed the source files.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: tests/unit/test_ticket_runner_gate_findings.py
  reason: 'T-0850''s own evidence tests for the SCOPED_RUN_FLAKY_RULE_IDS exclusion
    live in tests/unit/test_ticket_runner_gate_findings.py, the existing home for
    _check_gate_findings_fn/_check_gates_summary_fn unit tests, outside the ticket''s
    original scope list.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn::test_scoped_run_flaky_rule_excluded_from_findings
- tests/unit/test_ticket_runner_gate_findings.py::TestCheckGatesSummaryFn::test_scoped_run_flaky_rule_excluded_from_error_count
- tests/unit/test_ticket_runner_gate_findings.py::TestCheckGatesSummaryFn::test_unparsable_errors_section_falls_back_to_raw_summary_count
designated_repro_test: null
threat: null
component: null
---
T-0846 fixed land's ClaimDivergence gate-state check to refuse only on an
INCREASE in error count (real_errors > claims.gate_errors), which closes
the dominant failure mode (main-side fixes/drift lowering the count between
done-report time and post-merge land time). It does not close the WAIVE004
half of the same ticket: a frob:waive directive that self-declares
"known-flaky for diff-scoped rules" (per frob.gates's WAIVE004 doc) still
counts toward the scoped-run error total either way, so a flaky WAIVE004
appearing between done-report time and land time can still push the count
up and cause a false refuse.

Closing this soundly needs check_gates() to expose per-finding identity
(rule id + location), not just an (errors, warnings, waived) int triple,
so land can exclude findings whose rule self-declares scoped-run flakiness
from the comparison set. That requires touching src/frob/gates/** and/or
src/frob/check.py (the check-summary parsing) and the check_gates callable
built in src/frob/app/ticket_runner.py -- all outside T-0846's declared
scope (src/frob/tickets/_land.py, src/frob/tickets/**).

Plan: extend the check-summary parse to carry a frozenset of (rule_id,
location) finding identities alongside the int counts (or replace the int
triple with a richer type), thread it through check_gates's return type,
and have _reverify_done_report_claims_post_merge compare the SET difference
(post-merge findings minus pre-merge claimed findings, minus any rule id
in frob.gates's known-flaky-for-diff-scoped-rules set) instead of a raw
count increase.