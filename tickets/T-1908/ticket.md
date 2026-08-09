---
id: T-1908
title: 'test_dispatch_table_verbs_are_all_accounted_for fails: verbs debt/deprecated/wave
  unaccounted'
state: queued
kind: bug
origin: human
created: '2026-08-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_ticket_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Found while working T-1905 (unrelated to that ticket's EvidenceCmdSilent
root cause -- discovered as an incidental 9th failure in the same
pytest run but with a distinct error).

tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for
fails on main with:

  AssertionError: verb(s) ['debt', 'deprecated', 'wave'] exist in the
  real _ticket_dispatch_table() but are not accounted for by
  TestLedgerAutoCommitEnumeratedOverDispatchTable

Some prior change added 'debt', 'deprecated', and 'wave' verbs to
frob.app.ticket_runner._ticket_dispatch_table() without updating this
test's bookkeeping (_MUTATING_VERB_INVOCATIONS / _READ_ONLY_VERBS /
_NEEDS_DEDICATED_FIXTURE / _LEDGER_TRANSACTIONAL_VERBS). Needs someone
familiar with those three verbs to classify each correctly and update
the test.