---
id: T-5780
title: 'TIER003: epic closer -- all stories done plus a named outcome check recorded
  on the epic'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-5749
- T-5756
- T-5763
parent: T-5748
tier: ticket
sprint: ledger-tiers
runs_last: false
milestone: v0.536.0
points: 5
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/gates/_tickets_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '5'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
TIER003: epic closer -- all stories done PLUS a named outcome check (invariant or measured metric) recorded on the epic itself. Lands at WARN.

Positive control: an epic with all stories done but no outcome-check field fails TIER003 (expected to catch several of the 42 existing epics); an epic with the field bound and satisfied passes and stays quiet.

Doc page: docs/modules/tickets-lifecycle.md

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).

## Unblock log
- 2026-09-24: unblocked by T-draft-151e03f4 -- 2026-09-24: dangling draft id; the land runner promoted this blocker to its real T-#### id without rewriting the edge, real-id edge re-added via frob ticket block
- 2026-09-24: unblocked by T-draft-9570bf46 -- 2026-09-24: dangling draft id; the land runner promoted this blocker to its real T-#### id without rewriting the edge, real-id edge re-added via frob ticket block
