---
id: T-1043
title: 'fix test_unowned_deletions_diff_failure_after_merge: filter .frob/derived.lock
  like other scratch artifacts'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestGitSubprocessFailures::test_unowned_deletions_diff_failure_after_merge
designated_repro_test: null
threat: null
component: null
---
test_unowned_deletions_diff_failure_after_merge asserted raw git status --porcelain == '' on the worktree post-abort, but mutation-evidence's derived_state_lock (T-.. mutation evidence pre-land check) legitimately leaves .frob/derived.lock behind in the wt as a scratch artifact -- same class as .frob/land.lock which _status_ignoring_frob (T-0577) already exists to filter. This assertion predates that helper's use here and was never updated. Fix: use _status_ignoring_frob(wt) instead of the raw check, matching every other similar assertion in this file. No production code change -- land() behavior is correct, only the test assertion was too strict.