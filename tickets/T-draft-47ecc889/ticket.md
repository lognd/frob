---
id: T-draft-47ecc889
title: Add due dates on milestones and sprints and explicit rank within a parent
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: null
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
- src/frob/tickets/_models.py
- src/frob/tickets/__init__.py
- src/frob/_cli_parsers/_ticket/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_models.py
  reason: coord tree scope (COORD-TREE.md)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: coord tree scope (COORD-TREE.md)
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/_cli_parsers/_ticket/**
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
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Add due (date) to milestones and sprints and rank (explicit ordering within a parent, per milestone/sprint backlog) to the ticket model, with frob verbs to set them (milestone due, sprint due, ticket rank <id> --before/--after/--top) and a default rank derivation (priority, then blocked_by depth, then age) when unset. Owner decision 2026-09-24: forecasts and the cut line depend on these; the future UI's drag-to-reorder is this field. Positive control: two tickets in one sprint reorder deterministically and the order survives a ledger round-trip; a milestone without due reports none, never a fake date.
