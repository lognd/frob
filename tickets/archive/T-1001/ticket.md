---
id: T-1001
title: 'land: report stacked-sibling absorption as clean success, not CommitFailed'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: high
parent: T-0999
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_after_full_success_reports_absorption_not_commit_failed
- tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_after_finalize_then_squash_failure_lands_the_diff
- tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_when_still_queued_re_runs_the_ordinary_transition
designated_repro_test: null
acceptance:
- text: given a worktree whose earlier land already carried this ticket's files and
    ledger state, when this ticket lands, then land exits success reporting absorption
    and naming the absorbing commit
  evidence:
  - tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail::test_retry_after_full_success_reports_absorption_not_commit_failed
threat: null
component: null
---
Churn item 2 (~8 occurrences): a siblings-absorbed land stages an empty squash and the final commit exits 1 with no stderr, surfaced as CommitFailed; the coordinator hand-verifies state+content every time. Detect the empty stage, verify the ticket is done on main with its scoped content present, and report absorbed-by-prior-land success (naming the absorbing commit).