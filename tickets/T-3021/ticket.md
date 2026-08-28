---
id: T-3021
title: 'blocked_by never auto-clears: 8 queued tickets are hidden from doable by blockers
  that are already done or dropped'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'investigation-only: verifying the auto-clear premise before
  deciding whether a fix is needed'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Failure log
- 2026-08-28 attempt 1: premise stale: verified via direct enumeration of all 218 tickets with non-empty blocked_by (load_queue + _open_blockers, current main) that _OPEN_STATES already excludes DONE/DROPPED from blocking (frob/tickets/__init__.py _OPEN_STATES, pre-existing) and doable() returns 112 doable tickets with the only 3 doable_blocked entries caused by genuine scope-lease collisions (T-3188/T-1661/T-3077), none by a stale blocked_by. Checked candidate queued tickets whose blockers are all terminal (T-1686/T-3053/T-3063/T-3102): all but T-1686 already appear in doable(); T-1686 is excluded by scope-lease collision, not blocked_by. No queued ticket is currently hidden by a terminal blocker. T-2104 (landed Aug 21, before this Aug 26 filing) already fixed the adjacent narrowed-scope self-heal gap; the described auto-clear bug does not reproduce on current main.
