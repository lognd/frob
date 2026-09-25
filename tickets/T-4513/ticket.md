---
id: T-4513
title: C# and Unity support for frob (owner directive 2026-09-16)
state: queued
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
parent: null
tier: epic
sprint: null
runs_last: false
milestone: 0.533.0
flavour: null
due: null
rank: null
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
- tickets/T-CSUNITY-EPIC/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: tier
  old_value: ticket
  new_value: epic
  reason: epic for C#/Unity sprint v0.533.0 per owner directive
  actor: logan
  at: '2026-09-16'
- field: sprint
  old_value: v0.533.0
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
body_changes:
- mode: append
  reason: TIER003 outcome-check, epic audit E3 (T-5776)
  actor: logan
  at: '2026-09-25'
  old_length: 532
  new_length: 766
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Owner directive 2026-09-16: bring C# to end-to-end parity and add Unity support (Unity project model, .NET BCL + Unity API capability maps, NUnit/UnityTest evidence, fixture project). See design doc / stories for measured starting state: no C# capability resolver wired into _capability_scan.py, no NUnit/UnityTest collector, T-3232/T-3234/T-3856 are prerequisite cross-cutting bugs (linked, not duplicated), T-1597/T-1598 are the general umbrella (not duplicated -- this epic pulls C#/Unity out of that backlog per owner priority).

frob:outcome-metric all children done (5/5: T-4506, T-4509, T-4516, T-4518, T-4561); C# and Unity support landed end-to-end (adapter parity, fixture project, test-evidence collection, project model, post-land COV002 residue closed).