---
id: T-2646
title: 938 stale local branches are accumulated debt -- needs a stranded-work analysis
  before pruning
state: queued
kind: feature
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/guides/agent-playbook.md
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
This repo currently carries 938 local branches against 35 worktrees
(measured during T-2629, 2026-08-19) -- branches outnumber worktrees
~27x. Most correspond to landed or abandoned agent work and are never
cleaned up. Even a FAST scan over 938 branches is wasted work, and this
is exactly the scale that made T-2629's inline unlanded-branch-work scan
inside `frob ticket doable` structurally unable to complete.

Filed separately per T-2629's own instruction not to fold this in.
Related to, but distinct from, T-2599/T-2617's worktree audit (35
worktrees, 0 STRANDED at last measurement) -- that covered worktree
registrations, not the much larger set of local branches.

Do NOT delete branches as part of this ticket's filing -- deleting
branches is destructive and needs its own stranded-work analysis (which
branches are genuinely landed/abandoned vs. still live), exactly like the
worktree audit did before removing anything. This ticket is the analysis
step: enumerate branches, classify each as landed / abandoned / live /
unknown against `main`, and produce a pruning plan (or a
`frob worktree sweep`-shaped mechanism extended to branches) before any
deletion happens.
