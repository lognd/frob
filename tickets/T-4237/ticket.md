---
id: T-4237
title: classify a documented command's path arguments by execution context (container
  namespace vs host) against declared mounts
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
Consumer F-325/M2-1: a bound test checks a runbook's structure and file/service existence but cannot distinguish 'this path exists in the repo' from 'this path exists in the namespace the command runs in'. Cheap bounded version: flag any host-side path under a mount point compose declares as a named volume. Not fixture-testable in frob's own tree: no containers/compose files exist here.