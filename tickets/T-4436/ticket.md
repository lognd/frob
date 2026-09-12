---
id: T-4436
title: Draft-id finalizer rewrote a lost draft id to an unrelated real ticket in a
  worktree's Done report
state: queued
kind: bug
origin: agent
created: '2026-09-12'
priority: high
parent: null
tier: ticket
sprint: v0.532.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- tests/unit/test_land_finalize_drafts*.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED 2026-09-12 in worktree .claude/worktrees/t-4428: two minutes after the agent's commit eb067d5a7 (11:23), an UNCOMMITTED tool-made edit (file mtime 11:25) rewrote every literal `T-draft-858a1bad` in tickets/T-4428/ticket.md and tickets/T-4428/done-report.md to `T-4383`, plus a CHANGELOG.md edit. T-4383 is "T-0843 archive live-lease guard defeated by T-4172 stale-lease reconciliation" -- an unrelated ticket; the draft T-draft-858a1bad was LOST before promotion (T-4426's whole subject). So the draft-id finalizer (T-1495 `_land_plan_finalize_drafts` or the TICK006 recovery path -- whichever ran during the killed 2026-09-11 T-4428 land attempt) maps a dead draft id to a wrong real id and silently changes the meaning of a Done report. I discarded the edit with git checkout. ACCEPTANCE: (1) a draft id with no promotion record is never rewritten; (2) the mapping source is logged (draft -> real id, and where the record came from); (3) a test with a dead draft id in a ticket body asserts the body is untouched. See auto-recovery-refiles-renamed-drafts.
