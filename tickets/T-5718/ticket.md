---
id: T-5718
title: 'WIP limits and dead-WIP detection: start refuses beyond the limit, WIP001
  findings'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
blocked_by:
- T-draft-4ad886c1
parent: T-5630
tier: ticket
sprint: coord-surface
runs_last: false
milestone: v0.535.0
points: null
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
- src/frob/app/config.py
- src/frob/tickets/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/config.py
  reason: coord tree scope (COORD-TREE.md)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: coord tree scope (COORD-TREE.md)
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: sprint
  old_value: null
  new_value: coord-surface
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-24'
- field: parent
  old_value: null
  new_value: T-5630
  reason: coord/agent/ci command-surface epic (owner decision 2026-09-24)
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
WIP limits and dead-WIP detection (todo-hell): a config [coord] wip_per_agent (default 2) and wip_fleet; frob ticket start refuses beyond the limit unless --wip-override <reason> (stamp-of-approval tier); a gate rule (WIP001 family) reports in-progress tickets with no live lease older than N hours, and in-progress tickets older than the sprint length, each with the named fix (finish, land, or return to queued); coord status shows counts per agent. Measured 2026-09-24: 20 in-progress with a lease, 35 by state count, 7 agents actually working. Positive control: a fixture with 3 in-progress tickets for one agent and limit 2 refuses the fourth start and reports one finding; under the limit stays quiet. Owner decision 2026-09-24.
