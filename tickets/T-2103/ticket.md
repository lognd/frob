---
id: T-2103
title: 'T-2079 residue: 4 tests in test_ticket_leases.py fail (anchor verb + ownership
  guard not accounted for)'
state: queued
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tests/test_ticket_leases.py
- src/frob/tickets/_leases.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Found while working T-2093 (unrelated ticket): 4 tests in
tests/test_ticket_leases.py fail against current main, reproduced
identically at both HEAD and at T-2093's pre-fix parent commit
(confirming they predate T-2093 entirely):

  TestRefusesForeignLiveLease::test_expired_lease_in_another_worktree_does_not_block
  TestStealOverride::test_steal_succeeds_and_invalidates_the_other_worktrees_lease
  TestDoubleDispatchIncidentRegression::test_incident_shape_end_to_end
  TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for

The last one names the mechanism directly:

  AssertionError: verb(s) ['anchor'] exist in the real
  _ticket_dispatch_table() but are not accounted for by
  TestLedgerAutoCommitEnumeratedOverDispatchTable

The other three appear to fail via the new T-2079 ownership guard
(TicketOwnershipViolation) rejecting writes that used to be allowed --
e.g. test_incident_shape_end_to_end's captured log shows:

  ERROR ownership-guard: refusing to write T-0001 from .../wt -- it is
  currently leased to worktree .../main

Likely root cause: T-2079 added a new `anchor` verb/dispatch entry and a
write-ownership guard, and this test file's own coverage (the
enumerated-dispatch-table sentinel test, plus the lease/steal fixtures)
was not updated to match. Reproduce with:

  uv run pytest -o addopts="" tests/test_ticket_leases.py -q

Out of scope for T-2093 (declared scope is src/frob/tickets/_leases.py
plus tests/test_ticket_leases.py for T-2093's own fix only) -- filing
rather than fixing silently.
