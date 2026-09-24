---
id: T-5772
title: Promote TIER001-006 from WARN to ERROR after the migration
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-draft-d7c9c6c6
- T-5776
- T-5766
parent: T-5748
tier: ticket
sprint: ledger-tiers
runs_last: false
milestone: v0.536.0
points: 2
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
- src/frob/gates/_strata_milestone_closure.py
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
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Promote TIER001-006 from WARN to ERROR after the migration (T-0969 pattern): once E2 (story/invariant reclassification) and E3 (epic audit) are landed, flip the family's severity so the day the rules landed did not red every existing epic but the ledger is now held to them.

Positive control: with E2/E3 landed, frob check reports zero TIER findings at ERROR on the real ledger; a fixture epic lacking an outcome check is reported at ERROR, not WARN.

Doc page: docs/modules/tickets-lifecycle.md

Tree: /tmp/claude-1000/-home-logan-projects-frob/f95beb8e-97d5-4dd4-9038-3ffab8a3a4ea/scratchpad/LEDGER-TIERS-TREE.md (sections 2 and 5; section 5 overrides).
