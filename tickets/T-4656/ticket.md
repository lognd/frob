---
id: T-4656
title: 'Layering enforcement: [arch.layering] ledger < leases < land < app, gates
  independent, ARCH10x red'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
parent: T-4651
tier: story
sprint: null
runs_last: false
milestone: 0.535.0
flavour: user_story
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: 'tier=epic/story rollup for the kernel-decoupling epic:
  all file work lives in the leaf children; this ticket carries no write lease by
  design'
triage_changes:
- field: sprint
  old_value: v0.535.0
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: flavour
  old_value: null
  new_value: user_story
  reason: 'E2 (T-5766): census-based flavour classification (heuristic per E1''s own
    candidate signal)'
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
LAYERING concern of the kernel-decoupling epic (T-4651): the enforcement that makes the other four stories irreversible.

`[arch.layering]` already exists in frob.toml as an inert worked example (T-0620: schema present, `check_layering_violations` never wired into `frob check`). This story wires it and declares the kernel contract:

  ledger < leases < land < app,  with gates INDEPENDENT of all four.

Meaning: leases may import ledger; land may import leases and ledger; app may import all three; nothing may import upward; gates imports none of them and none of them import gates. A violation is ARCH10x RED in `frob check`, not a warning.

Also in this story: `frob cycle` clean on src/frob/tickets (today the module graph there is cyclic, which is why the four concerns cannot be separated by reading alone), and the shared-kernel extraction tickets already queued against the graph concerns.

Without this story the other four stories decay back into coupling within a sprint. This is the story that makes the boundary a build failure.
