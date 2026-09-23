---
id: T-5295
title: DOC006 no longer flags backticked future-verb phrasing in ticket bodies
state: done
kind: bug
origin: human
created: '2026-09-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
points: 2
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_ticket_2691_doc006.py
- src/frob/gates/_docptr.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '2'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-22'
evidence:
- tests/unit/test_ticket_2691_doc006.py::TestTicket2691Doc006Regression::test_backticked_future_verb_is_flagged
- tests/unit/test_ticket_2691_doc006.py::TestTicket2742Doc006Regression::test_backticked_future_verb_is_flagged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5295
branch: t-5295
---
gh run 35717833933; re-verified on dev tip 3acf8c6b30: TestTicket2691Doc006Regression::test_backticked_future_verb_is_flagged and TestTicket2742Doc006Regression::test_backticked_future_verb_is_flagged both fail (found == []). Captured log shows load aborted: ticket.md malformed frontmatter -- ticket-queue load failure inside the gate now swallows the DOC006 exemption path entirely instead of flagging.