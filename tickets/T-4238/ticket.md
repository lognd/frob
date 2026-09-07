---
id: T-4238
title: 'deploy-script semantic checks: an image a script pulls must be one a job pushes;
  an unauthenticated smoke check must not assert against an admin-guarded route'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: medium
parent: T-4135
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates
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
Consumer F-325/M2-4: two checks beyond existing pinning verification: (a) every image name a deploy script pulls is an image some job pushes (within-file string-set comparison); (b) a smoke-check URL must not name a route whose handler declares an admin/auth guard -- frob already resolves route symbols for guard-inventory purposes, so both halves of this contract violation are in its index. Not fixture-testable in frob's own tree: no deploy workflows or guarded routes exist here.