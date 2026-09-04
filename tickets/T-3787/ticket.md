---
id: T-3787
title: 'frob land: support landing onto a non-main target branch (unblocks off-main
  v1.0.0 dev after alpha)'
state: queued
kind: feature
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: capture branch-landing requirement + post-alpha release-hygiene rationale
  actor: logan
  at: '2026-09-04'
  old_length: 0
  new_length: 1273
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

frob's land flow is currently hardcoded to land onto `main` (src/frob/tickets/_land.py, "squash-apply onto main"), and the root-write guard forces all work through leased worktrees off main. This ticket adds support for landing a ticket's worktree onto a configurable NON-MAIN target branch.

## Why (release hygiene, user directive 2026-09-04)

After the alpha (a green release), remote `main` must stay frozen at that green release -- NOT dirtied by new development -- until a SECOND green release with more functionality is confirmed. This feature lets post-alpha v1.0.0 development land onto a dedicated dev branch (with full frob gates/accounting) instead of main, so the published remote main stays green while new work accumulates and is proven, then merged/pushed only when the second release is green.

## Sequencing

Deferred until AFTER the alpha is cut. Pre-alpha work (win32 drain to real-green, flaky layer) takes priority. This is the first defined v1.0.0 feature.

## Acceptance (sketch)

- `frob ticket land` accepts a target branch (flag or config), defaulting to main (backward compatible).
- Land-proof / ledger / gates operate against the chosen target branch, not assuming main.
- The root-write guard and worktree flow remain intact.
