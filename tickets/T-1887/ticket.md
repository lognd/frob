---
id: T-1887
title: test_tier_a_handlers_dict_covers_every_batch_rule missing TICK006 in expected
  set
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestFixEngineTierABatch2::test_tier_a_handlers_dict_covers_every_batch_rule
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Pre-existing, found while working T-1870 (unrelated): tests/test_gates.py::TestFixEngineTierABatch2::test_tier_a_handlers_dict_covers_every_batch_rule fails on main (verified directly, before any T-1870 edits) with 'Extra items in the left set: TICK006' -- TIER_A_HANDLERS now includes a TICK006 entry some later commit added without updating this test's hardcoded expected set. Fix: add TICK006 to the test's expected set (with a ticket-id comment matching this file's own convention).