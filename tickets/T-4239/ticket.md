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
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata
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
Consumer F-325/M2-6: a script's shebang says sh, its declared runtime image is alpine (busybox userland), and shellcheck ran with the default sh dialect misses a non-POSIX GNU extension (head -n -N). Bind a shell component to its runtime image (a strata node attribute) and run shellcheck with the matching dialect/compat list, or run the script's own tests inside that image. Not fixture-testable in frob's own tree: no shell-scripts-bound-to-container-images exist here.