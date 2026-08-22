---
id: T-2123
title: frob ticket new accepts an unacknowledged over-broad scope; enforcement point
  is missing at filing time, not just start
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_new_renumber.py
- tests/unit/test_new_ticket_over_broad_scope_warning.py
evidence_scope:
- tests/unit/test_new_ticket_over_broad_scope_warning.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_new_ticket_over_broad_scope_warning.py
  reason: BUG002 evidence for T-2123 lives in this test file
  actor: logan
  at: '2026-08-17'
evidence:
- tests/unit/test_new_ticket_over_broad_scope_warning.py::TestWarnOverBroadScopeOnNew::test_over_broad_scope_warns_at_filing_time
- tests/unit/test_new_ticket_over_broad_scope_warning.py::TestWarnOverBroadScopeOnNew::test_precise_scope_is_silent_at_filing_time
- tests/unit/test_new_ticket_over_broad_scope_warning.py::TestWarnOverBroadScopeOnNew::test_ack_bypasses_the_warning
- tests/unit/test_new_ticket_over_broad_scope_warning.py::TestWarnOverBroadScopeOnNew::test_severity_scales_with_a_catastrophic_match_count
designated_repro_test: tests/unit/test_new_ticket_over_broad_scope_warning.py::TestWarnOverBroadScopeOnNew::test_over_broad_scope_warns_at_filing_time
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 4f38aad1908230442c1a7f17808124be95323063
---
Coordinator measured 2026-08-11: 'frob ticket new --scope src/frob/app/ticket_runner/' (a whole-directory glob) was ACCEPTED, emitting 614 scope-closure warnings (8 shown, 606 collapsed). T-2094 (dropped, see its Done report) confirmed start-time enforcement already exists (T-1866) -- this is a DIFFERENT, earlier gap: the over-broad scope enters the ledger and can suppress the doable queue for other agents from the moment of filing, not just from start. Extend the same TICK009/large_glob_warnings breadth measure and scope_breadth_ack escape hatch T-1866 already established to the new_ticket path. Also: the collapsed-warning display (8 shown of 614) makes a catastrophic scope look like a minor nit -- severity/prominence should scale with the collapsed count.