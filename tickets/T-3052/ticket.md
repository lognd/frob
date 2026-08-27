---
id: T-3052
title: 'Land H5: the rolling baseline is written before the outcome is decided, so
  an unfilable finding is silently certified green after one wake'
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/verify/_worker.py
- docs/modules/tickets-verify-sweep.md
- tests/unit/verify/test_worker.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/verify/_worker.py
  reason: 'H5 fix: baseline write must be outcome-aware'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/modules/tickets-verify-sweep.md
  reason: 'H5 fix: baseline write must be outcome-aware'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/verify/test_worker.py
  reason: evidence tests for the H5 fix
  actor: logan
  at: '2026-08-26'
evidence:
- tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_unfilable_finding_still_pins_the_watermark_on_the_next_wake
- tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_new_findings_that_cannot_be_filed_still_do_not_advance
- tests/unit/verify/test_worker.py::TestRunCoalescedVerification::test_new_findings_filed_to_a_real_ticket_still_advance
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
