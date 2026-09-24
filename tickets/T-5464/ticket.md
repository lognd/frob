---
id: T-5464
title: 'TICK008 noise: Ticket model missing branch/worktree lease fields'
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: 3
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: points
  old_value: null
  new_value: '3'
  reason: ticket sizing
  actor: logan
  at: '2026-09-24'
- field: points
  old_value: '3'
  new_value: '3'
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
Found while draining CI run 35951365410 (dev 9e0c89bb19). Failing:
tests/gates_suite/test_tick.py::TestTick008UnknownLedgerFields::test_real_repo_ledger_is_tick008_clean

TICK008 fires 239 WARN violations against the real tickets/ ledger, all
"unknown ledger field 'branch'" / "unknown ledger field 'worktree'".
frob ticket work writes branch: and worktree: frontmatter onto every
in-progress ticket (the cross-worktree lease side-channel) but the
Ticket pydantic model (src/frob/tickets/_models.py) never declared them
as real fields, so pydantic's extra="allow" captures them as unknown
extras and TICK008 (correctly) flags every one.

Fix: add branch: str | None and worktree: str | None as declared Ticket
model fields (this is exactly the "schema-owning feature lands" case
TICK008's own docstring names as the intended resolution path) -- not a
ledger hand-edit, and not loosening TICK008 itself.
