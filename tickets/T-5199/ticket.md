---
id: T-5199
title: 'ticket_runner _close_cmd/_lifecycle: batch repeated load_queue calls (M4/M5)'
state: done
kind: bug
origin: human
created: '2026-09-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_lifecycle.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-5199 BUG002: pure perf batching, no intended behavior change'
  actor: logan
  at: '2026-09-21'
  old_length: 346
  new_length: 523
evidence:
- tests/unit/test_close_blocked_by_guard.py::TestOpenBlockersAtClose::test_open_blocker_names_the_open_ticket_not_the_terminal_one
- tests/unit/test_close_t1648_remainder.py::TestRemainderDisclosureGuard::test_allows_when_filed_ticket_is_open
- tests/unit/test_close_promote_drafts.py::TestClosePromotesPendingDrafts::test_close_promotes_a_draft_the_ticket_filed
- tests/test_ticket_work_and_land_finish.py::TestRootIsItselfANestedWorktree::test_work_cluster_refuses_from_a_nested_worktree
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5199
branch: t-5199
---
found while working T-5135 perf audit (M4/M5, lower priority, not fixed there to stay in the H2-H5/M7 fix order the ticket specified): frob ticket work --cluster and frob ticket close each call load_queue multiple times (four loads measured) instead of loading once and threading the queue through. Batch to one load_queue per command invocation.

frob:no-behavior-change reason="batches redundant load_queue calls (M4/M5 perf follow-up); observable behavior of close/work --cluster is unchanged, only I/O count is reduced"