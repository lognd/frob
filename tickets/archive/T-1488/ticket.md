---
id: T-1488
title: 'tests: promote _make_design_worktree to shared conftest helper if a second
  module needs it'
state: done
kind: docs
origin: human
created: '2026-08-03'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestLandPlan::test_merges_and_finalizes_every_draft_atomically
designated_repro_test: null
threat: null
component: null
---
tests/test_ticket_land.py::_make_design_worktree (T-1269) builds a
design-phase worktree fixture (docs/ledger changes, no closeable ticket)
for TestLandPlan's five test methods, in this same file. It has no
caller outside its own file's tests today (WIRE001), waived with this
follow-up. Promote to a shared conftest helper if a second test module
needs an identical design-phase worktree fixture.