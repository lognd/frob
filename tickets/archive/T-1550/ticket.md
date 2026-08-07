---
id: T-1550
title: attribute branch-history waive deletions to the sibling ticket that landed
  them (kill the OutOfScopeWaiveDeletion re-declare round)
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land_git_ops.py
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: 'Narrowing to the waive-deletion attribution scan and its land-check

    callers/tests per the ticket body''s fix description.

    '
  actor: logan
  at: '2026-08-05'
- op: add
  glob: src/frob/tickets/_land.py
  reason: 'Narrowing to the waive-deletion attribution scan and its land-check

    callers/tests per the ticket body''s fix description.

    '
  actor: logan
  at: '2026-08-05'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'Narrowing to the waive-deletion attribution scan and its land-check

    callers/tests per the ticket body''s fix description.

    '
  actor: logan
  at: '2026-08-05'
evidence:
- tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_already_landed_sibling_deletion_on_shared_worktree_not_recounted
- tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_committed_out_of_scope_undeclared_waive_deletion_refuses_before_merge
- tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_committed_in_scope_waive_deletion_is_allowed
- tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_merge_base_drift_deletion_on_main_side_not_counted
- tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_branch_merges_main_after_main_deletes_a_waiver_still_allowed
designated_repro_test: null
threat: null
component: null
---
The land waive-deletion scan walks ALL branch commits since merge-base and attributes every deletion to the LANDING ticket, so on a multi-ticket branch each subsequent land refuses on deletions its already-landed siblings own (T-1225, T-1444 each burned a full land round on this 2026-08-05). Fix: before refusing, check whether the deletion's containing commit is already an ancestor of main (sibling landed) or the deletion falls inside a ticket that is done on main whose scope covers the file -- if so, log and skip. Kills the declare-in-report boilerplate round entirely.