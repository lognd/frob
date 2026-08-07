---
id: T-0479
title: 'frob ticket land: auto-reconcile the ledger and non-owned code conflicts so
  no manual restore recipe is ever needed -- (a) splice ONLY the landed ticket''s
  own block onto main''s CURRENT tickets.md (restore-from-main + single-writer apply
  of state+done-report+evidence), never carrying the worktree''s stale sibling-ticket
  states; (b) auto-resolve merge conflicts in files OUTSIDE the ticket''s declared
  scope by taking main''s version (the worktree never legitimately changed them);
  only surface conflicts in IN-SCOPE files for manual resolution. Implements the coordinator''s
  hand-run restore recipe (playbook 10b) as land behavior. Subsumes T-0475.'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'T-0479 implementation: ledger splice ticket-scoping + out-of-scope conflict
    auto-resolve'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'T-0479 implementation: ledger splice ticket-scoping + out-of-scope conflict
    auto-resolve'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tickets.md
  reason: 'T-0479 implementation: ledger splice ticket-scoping + out-of-scope conflict
    auto-resolve'
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_ticket_land.py::TestSpliceOnlyTicket::test_sibling_state_never_taken_from_worktree
- tests/test_ticket_land.py::TestSpliceOnlyTicket::test_landed_tickets_own_divergence_still_resolved
- tests/test_ticket_land.py::TestOutOfScopeConflictAutoResolved::test_conflict_outside_scope_takes_mains_side_and_lands
designated_repro_test: null
threat: null
component: null
---
