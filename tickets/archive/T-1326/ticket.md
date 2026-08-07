---
id: T-1326
title: 'land guard: catch frob:waive deletions in COMMITTED branch history, not just
  uncommitted state'
state: done
kind: security
origin: agent
created: '2026-07-29'
priority: high
blocked_by:
- T-1323
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_merge.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_committed_out_of_scope_undeclared_waive_deletion_refuses_before_merge
- tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_committed_in_scope_waive_deletion_is_allowed
- tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_committed_declared_in_done_report_waive_deletion_is_allowed
- tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_merge_base_drift_deletion_on_main_side_not_counted
designated_repro_test: null
acceptance:
- text: GIVEN a branch commit that deletes an out-of-scope undeclared frob:waive line
    WHEN frob ticket land runs THEN it refuses before merge naming file and rule
  evidence:
  - tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_committed_out_of_scope_undeclared_waive_deletion_refuses_before_merge
- text: GIVEN the same deletion but owned by a landing ticket's scope or properly
    declared THEN land proceeds
  evidence:
  - tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_committed_in_scope_waive_deletion_is_allowed
  - tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_committed_declared_in_done_report_waive_deletion_is_allowed
  - tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_merge_base_drift_deletion_on_main_side_not_counted
threat: tampering
component: null
---
T-1323's land-precheck guard (_check_uncommitted_waive_deletions) only inspects git diff HEAD (uncommitted worktree state) -- the exact incident mechanism. Reviewer finding at T-1323 approval: a frob:waive deletion COMMITTED to the branch before land is invisible to it, leaving a laundering vector (an agent or tool commits the deletion mid-ticket and it rides the merge). Extend the guard to also scan git diff merge-base..HEAD for single-line frob:waive deletions, applying the same scope-ownership and (tightened) Done-report declaration logic; a deletion neither owned by a landing ticket's scope nor declared is an ERROR-tier refusal. Also consider the multi-line/continuation waiver blind spot flagged MINOR in the same review (mirror of WAIVE004's own single-line scope) -- either cover it or scope the docstring honestly.