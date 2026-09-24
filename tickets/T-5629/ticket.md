---
id: T-5629
title: 'frob coord quarantine dispose --file-residue: file one residue ticket and
  dispose'
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
frob coord quarantine dispose --file-residue [--milestone M --points N]: when quarantine is raised, file ONE residue ticket carrying the undisposed findings grouped by rule id and file, dispose every finding against it through frob verify dispose, set milestone and points, and report the ticket id; refuse clearly if the filed id does not resolve on the root (the T-5439 phantom of 2026-09-23). Positive control: two undisposed findings sharing a rule id produce exactly one residue ticket. Retires dispose-noise.sh.
