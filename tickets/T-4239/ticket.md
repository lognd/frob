---
id: T-4239
title: bind a shell component to its runtime image and shellcheck/lint it with that
  image's actual dialect
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: low
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: 1.1.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.538.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.538.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consumer F-325/M2-6: a script's shebang says sh, its declared runtime image is alpine (busybox userland), and shellcheck ran with the default sh dialect misses a non-POSIX GNU extension (head -n -N). Bind a shell component to its runtime image (a strata node attribute) and run shellcheck with the matching dialect/compat list, or run the script's own tests inside that image. Not fixture-testable in frob's own tree: no shell-scripts-bound-to-container-images exist here.