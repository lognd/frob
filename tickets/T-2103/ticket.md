---
id: T-2103
title: 'T-2079 residue: 4 tests in test_ticket_leases.py fail (anchor verb + ownership
  guard not accounted for)'
state: done
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
- src/frob/app/ticket_runner/_lifecycle.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_lifecycle.py
  reason: "Investigation found the real root cause of 3 of the 4 named failures is\
    \ a\ngenuine T-2079 ordering/expiry gap, not a fixture bug:\n\n1. enforce_ticket_ownership\
    \ (_leases.py) does not treat an EXPIRED\n   cross-worktree lease as \"no live\
    \ holder\" -- every other reader of\n   leases in this file (_refuse_if_foreign_live_lease)\
    \ already applies\n   is_lease_ttl_expired before treating a lease as live, but\
    \ the new\n   ownership guard does not, so it wrongly refuses the T-0782 dead-agent\n\
    \   recovery path (test_expired_lease_in_another_worktree_does_not_block).\n\n\
    2. _refuse_if_foreign_live_lease (_lifecycle.py)'s --steal path documents\n  \
    \ that the re-pin happens later, inside transition(..., IN_PROGRESS)'s\n   own\
    \ _sync_cross_worktree_lease call -- but _auto_plan_if_queued's\n   earlier transition(...,\
    \ PLANNED) call writes the ticket FIRST and\n   trips enforce_ticket_ownership\
    \ against the OLD (still correctly-live)\n   lease before the re-pin ever happens,\
    \ so a genuine --steal now always\n   fails (test_steal_succeeds_and_invalidates_the_other_worktrees_lease,\n\
    \   test_incident_shape_end_to_end). Fixing this without weakening the\n   guard\
    \ requires moving the re-pin earlier, in _lifecycle.py.\n\nBoth are in _lifecycle.py\
    \ + _leases.py, both already in scope or a\none-file widen of it.\n"
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_ticket_leases.py::TestRefusesForeignLiveLease::test_expired_lease_in_another_worktree_does_not_block
- tests/test_ticket_leases.py::TestStealOverride::test_steal_succeeds_and_invalidates_the_other_worktrees_lease
- tests/test_ticket_leases.py::TestDoubleDispatchIncidentRegression::test_incident_shape_end_to_end
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for
designated_repro_test: tests/test_ticket_leases.py::TestRefusesForeignLiveLease::test_expired_lease_in_another_worktree_does_not_block
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