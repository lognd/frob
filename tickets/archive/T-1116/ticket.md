---
id: T-1116
title: 'test: test_every_deferred_entry_targets_an_open_ticket fails, zero deferred
  entries exist in weaknesses.yaml'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/weaknesses.yaml
- tests/test_registry_reconciliation_weaknesses.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_registry_reconciliation_weaknesses.py::TestWeaknessesExhaustiveness::test_every_deferred_entry_targets_an_open_ticket
designated_repro_test: null
threat: null
component: null
---
Found while working T-1037: tests/test_registry_reconciliation_weaknesses.py
::TestWeaknessesExhaustiveness::test_every_deferred_entry_targets_an_open_
ticket fails on current main with:

  AssertionError: expected at least one deferred entry to check against

docs/design/registry/weaknesses.yaml currently has ZERO entries whose
disposition.kind is DispositionKind.DEFERRED (confirmed via direct grep
and via _load_weaknesses()/DispositionKind filtering in the test itself).
Either every previously-deferred entry has since been resolved to
checkable/duplicate-of/out-of-scope (in which case the test's own
precondition assertion is now stale and should be relaxed to skip rather
than fail when the deferred set is legitimately empty), or a deferred
entry was dropped/miscategorized somewhere along the way and the test is
correctly catching a real regression -- needs investigation to tell
these apart before deciding the fix.

Out of T-1037's declared scope (that ticket is specifically about REG011
out_of_scope-reason substantive-disclosure, already independently fixed
by T-1019 before this wave started -- confirmed zero REG011 violations
and the ticket's own named regression test passing on current main).