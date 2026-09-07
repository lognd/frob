---
id: T-4229
title: 'runbook fenced shell commands: a doc-adjacent directive naming the execution
  container, checkable by lint or dry-run'
state: queued
kind: feature
origin: agent
created: '2026-09-07'
priority: low
parent: T-4175
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
Consumer F-373/P5 (T-4175): a unit test exercises a runbook script under a dry-run env var, but no test executes, parses, or lints the runbook's own documented fenced commands, and frob's doc gates check anchors and drift, not whether a documented shell command would actually run. Mark runbook code fences with a directive naming the container they run in, and lint/dry-run against it. Not fixture-testable in frob's own tree: no runbooks/containers exist here.