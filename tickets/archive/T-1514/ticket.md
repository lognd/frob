---
id: T-1514
title: run the unscoped error sweep pre-land on a merge-preview worktree instead of
  post-land on mutated main
state: done
kind: feature
origin: human
created: '2026-08-04'
priority: high
parent: null
tier: ticket
sprint: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestPreCommitUnscopedSweep::test_true_verdict_lands_normally
- tests/test_ticket_land.py::TestPreCommitUnscopedSweep::test_none_verdict_is_a_skip_lands_normally
- tests/test_ticket_land.py::TestPreCommitUnscopedSweep::test_false_verdict_unwinds_and_commits_nothing
- tests/test_ticket_land.py::TestPreCommitUnscopedSweep::test_no_callback_is_noop
- tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn::test_new_finding_fixed_by_tier_a_stages_and_returns_true
- tests/test_ticket_work_and_land_finish.py::TestPreCommitUnscopedSweepFn::test_new_finding_unresolved_by_tier_a_returns_false
designated_repro_test: null
threat: null
component: null
---
The T-1456 post-land unscoped sweep currently verifies AFTER the land commit exists on main, so a refusal requires reset --hard -- which is exactly what destroyed foreign interleaved commits on 2026-08-04 (see T-1495). Land already builds the merge result before committing; run the sweep against that merge preview in a scratch worktree (same mechanism as _spawn_baseline_snapshot_worktree) BEFORE any commit lands on main. A refusal then costs nothing and reverts nothing; the post-land sweep can remain as a cheap assertion.