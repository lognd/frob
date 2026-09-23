---
id: T-5378
title: 'test_dispatch_table_verbs_are_all_accounted_for: points/set/tokens verbs unclassified'
state: queued
kind: bug
origin: human
created: '2026-09-23'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-23'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35819358270 (ubuntu/windows); re-verified failing on dev tip 39b89ed091: tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for fails -- the real _ticket_dispatch_table() now has verbs 'points', 'set', 'tokens' (added by T-5132/T-5133-era work) that are not in any of the test's classification sets (_MUTATING_VERB_INVOCATIONS, _READ_ONLY_VERBS, _NEEDS_DEDICATED_FIXTURE, _LEDGER_TRANSACTIONAL_VERBS). File each verb into the correct bucket. T-5280 (done) fixed a related but distinct LEDGER_VERB_STRATEGY gap for points/tokens; this is the separate test-side accounting table in test_ticket_leases.py.