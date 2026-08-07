---
id: T-1468
title: land deletion filter reads fmt rewraps of frob:waive comments as deletions
state: done
kind: bug
origin: agent
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land_git_ops.py
- tests/test_ticket_land.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_land.py
  reason: regression tests for the waive rewrap-vs-deletion fix live in the existing
    land test suite
  actor: logan
  at: '2026-08-03'
- op: add
  glob: design/frob.strata
  reason: frob sys sync-interface auto-updates this file to declare the new TestWaiveRewrapNotDeletion
    test class this ticket adds; mandated side effect of the diff, not scope creep
  actor: logan
  at: '2026-08-03'
evidence:
- tests/test_ticket_land.py::TestWaiveRewrapNotDeletion::test_rewrap_only_diff_is_not_flagged_as_a_deletion
- tests/test_ticket_land.py::TestWaiveRewrapNotDeletion::test_rewrap_that_also_changes_content_still_refuses
- tests/test_ticket_land.py::TestUncommittedWaiveDeletionRefusal::test_out_of_scope_undeclared_waive_deletion_refuses_before_merge
- tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_committed_out_of_scope_undeclared_waive_deletion_refuses_before_merge
designated_repro_test: null
acceptance:
- text: GIVEN a diff that only re-flows a frob:waive comment's line wrapping WHEN
    the land deletion filter runs THEN it is not treated as a deletion
  evidence:
  - tests/test_ticket_land.py::TestWaiveRewrapNotDeletion::test_rewrap_only_diff_is_not_flagged_as_a_deletion
  - tests/test_ticket_land.py::TestWaiveRewrapNotDeletion::test_rewrap_that_also_changes_content_still_refuses
  - tests/test_ticket_land.py::TestUncommittedWaiveDeletionRefusal::test_out_of_scope_undeclared_waive_deletion_refuses_before_merge
  - tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_committed_out_of_scope_undeclared_waive_deletion_refuses_before_merge
- text: GIVEN a diff that genuinely deletes a frob:waive directive WHEN the filter
    runs THEN it still refuses as today
  evidence:
  - tests/test_ticket_land.py::TestWaiveRewrapNotDeletion::test_rewrap_only_diff_is_not_flagged_as_a_deletion
  - tests/test_ticket_land.py::TestWaiveRewrapNotDeletion::test_rewrap_that_also_changes_content_still_refuses
  - tests/test_ticket_land.py::TestUncommittedWaiveDeletionRefusal::test_out_of_scope_undeclared_waive_deletion_refuses_before_merge
  - tests/test_ticket_land.py::TestCommittedWaiveDeletionRefusal::test_committed_out_of_scope_undeclared_waive_deletion_refuses_before_merge
threat: null
component: null
---
Observed on the T-1465 land: the pre-land fmt absorb rewrapped two multi-line frob:waive WIRE001 comments in tests/conftest.py to fit the line-length limit; the deletion filter saw the minus-lines of the rewrap diff as waiver deletions and refused the land (OutOfScopeWaiveDeletion) even though the waiver text, rule, reason, and follow_up were byte-equivalent after re-flowing. The Done-report prose disclosure did not satisfy the check; only adding every touched file to the landing ticket's scope did. Fix: the filter should normalize waive directives (join continuation lines, collapse whitespace) on both diff sides and treat an identical-normalized-content rewrap as no deletion. Regression test: a diff that only re-wraps a waive comment passes the filter; a diff that actually removes one still refuses.