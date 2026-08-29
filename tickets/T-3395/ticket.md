---
id: T-3395
title: Reduce ARCH103 decision-point count in refactor._verify._import_check_env and
  app._version_guard._git_head_sha
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/refactor/_verify.py
- src/frob/app/_version_guard.py
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
ARCH103 fires on both single-concern helpers (subprocess env construction; git rev-parse + failure classification). Resolved via reasoned frob:waive ARCH103 -- both are single cohesive units where a further split would scatter one concern across artificial boundaries rather than reduce real complexity.